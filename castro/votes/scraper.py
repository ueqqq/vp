"""Async vote-site scraper.

Differences from the old one: nothing here blocks the event loop (the Cloudflare fetch runs in
a worker thread), sites are read in parallel, and a failed site returns None rather than quietly
handing back an old number. The engine decides what to do about missing data.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass

import aiohttp

from votes.parsing import parse_count

log = logging.getLogger("castro.scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class SiteHealth:
    ok: int = 0
    fail: int = 0
    consecutive_fail: int = 0
    last_ok: float | None = None
    last_error: str = ""


class VoteScraper:
    def __init__(self, sites: list[dict]):
        self.sites = sites
        self.session: aiohttp.ClientSession | None = None
        self.health = {s["name"]: SiteHealth() for s in sites}

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(headers={"User-Agent": USER_AGENT})

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def scrape_all(self) -> dict[str, int | None]:
        results = await asyncio.gather(*(self._scrape(s) for s in self.sites), return_exceptions=True)
        readings: dict[str, int | None] = {}
        for site, result in zip(self.sites, results):
            readings[site["name"]] = None if isinstance(result, BaseException) else result
        return readings

    async def _scrape(self, site: dict) -> int | None:
        name, health = site["name"], self.health[site["name"]]
        error = "no response"
        for attempt in range(3):
            html, error = await self._fetch(site)
            if html:
                count = parse_count(html, site["patterns"])
                if count is not None:
                    health.ok += 1
                    health.consecutive_fail = 0
                    health.last_ok = time.time()
                    health.last_error = ""
                    return count
                error = "page loaded but no vote count found (site layout may have changed)"
            if attempt < 2:
                await asyncio.sleep(2 ** attempt + random.random())
        health.fail += 1
        health.consecutive_fail += 1
        health.last_error = error
        log.warning("%s: %s", name, error)
        return None

    async def _fetch(self, site: dict) -> tuple[str | None, str]:
        url = site["url"]
        try:
            if site.get("cloudflare"):
                return await asyncio.to_thread(self._fetch_cloudflare, url)
            assert self.session is not None
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                return await resp.text(), ""
        except asyncio.TimeoutError:
            return None, "timed out"
        except Exception as exc:  # network errors are expected; never crash the loop
            return None, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _fetch_cloudflare(url: str) -> tuple[str | None, str]:
        try:
            import cloudscraper  # optional dependency
        except ImportError:
            return None, "cloudscraper not installed (pip install cloudscraper)"
        try:
            response = cloudscraper.create_scraper().get(url, timeout=20)
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        return response.text, ""
