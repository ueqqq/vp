"""
Reliable vote-count scraper for Minecraft server lists.

Design goals:
- Prefer stable HTTP extraction (BeautifulSoup + regex)
- Use cloudscraper only for sites known to sit behind Cloudflare
- Never poison the running total with partial failures — fall back to last good value
- Validate jumps so a bad parse cannot reset a cycle
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from config import BOT_NAME, VOTE_SITES

logger = logging.getLogger(BOT_NAME)

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    logger.warning("cloudscraper not installed — Cloudflare sites may fail")


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def _default_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }


class AdvancedVoteScraper:
    """Scrapes vote totals from configured listing sites."""

    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_successful_counts: Dict[str, int] = {}
        self.scrape_attempts: Dict[str, Dict[str, int]] = {}
        self.consecutive_failures: Dict[str, int] = {}
        self.site_health: Dict[str, dict] = {}
        self.scrape_history: List[dict] = []

        for site in VOTE_SITES:
            name = site["name"]
            self.scrape_attempts[name] = {"success": 0, "fail": 0}
            self.consecutive_failures[name] = 0
            self.site_health[name] = {
                "last_success": None,
                "last_error": None,
                "total_scrapes": 0,
                "successful_scrapes": 0,
            }

    async def start(self) -> None:
        if self.session is None or self.session.closed:
            # Let aiohttp negotiate compression (including Brotli if installed)
            self.session = aiohttp.ClientSession(headers=_default_headers())

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    # ─── Validation ───────────────────────────────────────────────────────────

    def _validate(self, name: str, count: int, previous: Optional[int]) -> bool:
        if count < 0 or count > 5_000_000:
            logger.warning("%s: rejected out-of-range count %s", name, count)
            return False
        if previous is not None:
            # Votes only go up; allow small downward noise (site resets are rare)
            if count + 50 < previous:
                logger.warning(
                    "%s: rejected suspicious drop %s -> %s", name, previous, count
                )
                return False
            if count - previous > 500:
                logger.warning(
                    "%s: suspicious jump %s -> %s (accepting, but logged)",
                    name, previous, count,
                )
        return True

    # ─── Extraction ───────────────────────────────────────────────────────────

    def _extract_beautifulsoup(self, html: str, site_name: str) -> Optional[int]:
        soup = BeautifulSoup(html, "html.parser")

        if site_name == "Minecraft-MP":
            for row in soup.find_all("tr"):
                strong = row.find("strong")
                if strong and "Vote" in strong.get_text():
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        m = re.search(r"(\d+)", cells[1].get_text())
                        if m:
                            return int(m.group(1))

        elif site_name == "MinecraftServers.org":
            for row in soup.find_all("div", class_="row"):
                cols = row.find_all("div", recursive=False)
                if len(cols) >= 2 and cols[0].get_text(strip=True) == "Votes":
                    m = re.search(r"(\d+)", cols[1].get_text())
                    if m:
                        return int(m.group(1))
            # Alternate layout: label/value pairs
            for label in soup.find_all(string=re.compile(r"^\s*Votes\s*$")):
                parent = label.parent
                if parent is None:
                    continue
                sibling = parent.find_next_sibling()
                if sibling:
                    m = re.search(r"(\d+)", sibling.get_text())
                    if m:
                        return int(m.group(1))

        elif site_name == "Minecraft-Server-List":
            text = soup.get_text(" ", strip=True)
            for pat in (
                r"(\d+)\s+Players have voted for this server",
                r"(\d+)\s+Votes\s*-\s*All time",
            ):
                m = re.search(pat, text, re.I)
                if m:
                    return int(m.group(1))
            for tag in soup.find_all(["b", "strong", "span", "div"]):
                t = tag.get_text(" ", strip=True)
                m = re.search(r"(\d+)\s+Votes\s*-\s*All time", t, re.I)
                if m:
                    return int(m.group(1))

        return None

    def _extract_regex(self, html: str, site: dict) -> Optional[int]:
        for pattern in site.get("fallback_patterns", []):
            try:
                m = re.search(pattern, html, re.I | re.S)
                if m:
                    return int(m.group(1))
            except (re.error, ValueError) as e:
                logger.debug("%s: bad pattern %r (%s)", site["name"], pattern, e)
        return None

    def _looks_like_challenge(self, html: str, status: int) -> bool:
        if status in (403, 503, 429):
            return True
        low = html[:4000].lower()
        markers = (
            "cf-browser-verification",
            "cf-challenge",
            "just a moment",
            "attention required",
            "cloudflare",
            "__cf_chl",
        )
        return any(m in low for m in markers)

    # ─── Fetch ────────────────────────────────────────────────────────────────

    async def _fetch_aiohttp(self, url: str, name: str) -> Tuple[Optional[str], int]:
        await self.start()
        assert self.session is not None
        try:
            # Rotate UA each request
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=25), allow_redirects=True
            ) as resp:
                html = await resp.text(errors="replace")
                if resp.status != 200:
                    logger.warning("%s: HTTP %s", name, resp.status)
                return html, resp.status
        except asyncio.TimeoutError:
            logger.warning("%s: timeout", name)
            return None, 0
        except Exception as e:
            logger.warning("%s: fetch error %s", name, e)
            return None, 0

    async def _fetch_cloudscraper(self, url: str, name: str) -> Tuple[Optional[str], int]:
        if not CLOUDSCRAPER_AVAILABLE:
            logger.warning("%s: cloudscraper missing", name)
            return None, 0

        def _sync_fetch() -> Tuple[Optional[str], int]:
            try:
                scraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "windows", "mobile": False}
                )
                r = scraper.get(url, timeout=30)
                return r.text, r.status_code
            except Exception as e:
                logger.warning("%s: cloudscraper error %s", name, e)
                return None, 0

        return await asyncio.to_thread(_sync_fetch)

    async def _fetch(self, site: dict) -> Tuple[Optional[str], int]:
        name = site["name"]
        url = site["url"]
        prefer_cf = bool(site.get("use_cloudscraper"))

        if prefer_cf:
            html, status = await self._fetch_cloudscraper(url, name)
            if html and not self._looks_like_challenge(html, status):
                return html, status
            # Fall through to plain HTTP once
            html2, status2 = await self._fetch_aiohttp(url, name)
            if html2 and not self._looks_like_challenge(html2, status2):
                return html2, status2
            return html or html2, status or status2

        html, status = await self._fetch_aiohttp(url, name)
        if html and self._looks_like_challenge(html, status):
            logger.info("%s: challenge detected, trying cloudscraper", name)
            return await self._fetch_cloudscraper(url, name)
        return html, status

    # ─── Bookkeeping ──────────────────────────────────────────────────────────

    def _record_success(self, name: str, count: int) -> None:
        self.last_successful_counts[name] = count
        self.scrape_attempts[name]["success"] += 1
        self.consecutive_failures[name] = 0
        health = self.site_health[name]
        health["successful_scrapes"] += 1
        health["last_success"] = datetime.now(timezone.utc).isoformat()
        health["last_error"] = None

    def _record_failure(self, name: str, reason: str) -> None:
        self.scrape_attempts[name]["fail"] += 1
        self.consecutive_failures[name] += 1
        self.site_health[name]["last_error"] = reason

    def _cached(self, name: str) -> Tuple[str, Optional[int]]:
        cached = self.last_successful_counts.get(name)
        if cached is not None:
            logger.info("%s: using last good value %s", name, cached)
            return name, cached
        logger.warning("%s: no cached value", name)
        return name, None

    # ─── Public API ───────────────────────────────────────────────────────────

    async def scrape_site(self, site: dict, max_retries: int = 2) -> Tuple[str, Optional[int]]:
        name = site["name"]
        self.site_health[name]["total_scrapes"] += 1

        for attempt in range(max_retries + 1):
            html, status = await self._fetch(site)
            if not html or self._looks_like_challenge(html, status):
                reason = f"blocked_or_empty status={status}"
                logger.warning("%s: %s (attempt %s)", name, reason, attempt + 1)
                if attempt < max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                self._record_failure(name, reason)
                return self._cached(name)

            previous = self.last_successful_counts.get(name)
            count = self._extract_beautifulsoup(html, name)
            if count is None:
                count = self._extract_regex(html, site)

            if count is not None and self._validate(name, count, previous):
                logger.info("%s: %s votes", name, count)
                self._record_success(name, count)
                return name, count

            logger.warning("%s: parse failed (attempt %s)", name, attempt + 1)
            if attempt < max_retries:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue

            self._record_failure(name, "parse_failed")
            return self._cached(name)

        self._record_failure(name, "exhausted_retries")
        return self._cached(name)

    async def scrape_all(self) -> Tuple[Dict[str, Optional[int]], int]:
        """
        Scrape every configured site.
        Returns (counts_by_name, total).
        Failed sites use last-known-good when available so the cycle total stays stable.
        """
        await self.start()
        counts: Dict[str, Optional[int]] = {}

        for i, site in enumerate(VOTE_SITES):
            name, count = await self.scrape_site(site)
            counts[name] = count
            if i < len(VOTE_SITES) - 1:
                await asyncio.sleep(0.8)

        total = sum(v for v in counts.values() if v is not None)
        self.scrape_history.append(
            {
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "counts": dict(counts),
                "total": total,
            }
        )
        if len(self.scrape_history) > 100:
            self.scrape_history = self.scrape_history[-100:]

        logger.info("Scrape complete: %s | total=%s", counts, total)
        return counts, total

    def get_stats(self) -> dict:
        return {
            "last_successful_counts": dict(self.last_successful_counts),
            "scrape_attempts": dict(self.scrape_attempts),
            "consecutive_failures": dict(self.consecutive_failures),
            "site_health": {k: dict(v) for k, v in self.site_health.items()},
        }
