"""Vote-party cycle logic. No Discord, no network: feed it readings, it tells you what happened.

Design rules (each one fixes a problem in the old bot):
  * vote totals on these sites are all-time counters, so they only ever go UP. A reading
    lower than the last one is a bad scrape and is rejected, never accepted.
  * a huge jump is held until a second scrape confirms it, instead of corrupting the baseline.
  * a failed site keeps its last known number but is reported as stale, never as fresh.
  * a cycle only starts once every site has been read at least once.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("castro.votes")

NORMAL, MOMENTUM, CLOSE, FINAL, CELEBRATION, WAITING = (
    "normal", "momentum", "close", "final", "celebration", "waiting",
)


def new_state(goal: int) -> dict:
    return {
        "goal": goal,
        "baseline": None,
        "cycle": 1,
        "counts": {},
        "last_ok": {},
        "pending": {},
        "checked": None,
        "cycle_started": None,
        "ping_sent": False,
        "last_party": None,
        "parties": [],
        "tracker": {"channel": None, "message": None},
    }


@dataclass
class ApplyResult:
    accepted: list[str] = field(default_factory=list)
    rejected: dict[str, str] = field(default_factory=dict)
    completed: bool = False
    should_ping: bool = False


class VoteEngine:
    def __init__(self, state: dict, sites: list[str], goal: int, ping_threshold: int,
                 max_jump: int = 500, stale_after: int = 900):
        self.state = state
        self.sites = sites
        self.goal = goal
        self.ping_threshold = ping_threshold
        self.max_jump = max_jump
        self.stale_after = stale_after
        for key, value in new_state(goal).items():  # tolerate older/partial saved files
            self.state.setdefault(key, value)

    # ── derived values ────────────────────────────────────────────────────────
    @property
    def ready(self) -> bool:
        return self.state["baseline"] is not None and all(s in self.state["counts"] for s in self.sites)

    @property
    def total(self) -> int:
        return sum(self.state["counts"].get(s, 0) for s in self.sites)

    @property
    def progress(self) -> int:
        if not self.ready:
            return 0
        return max(0, self.total - self.state["baseline"])

    @property
    def remaining(self) -> int:
        return max(0, self.goal - self.progress)

    def stale_sites(self, now: float) -> list[str]:
        last_ok = self.state["last_ok"]
        return [s for s in self.sites if now - last_ok.get(s, 0) > self.stale_after]

    def phase(self, now: float) -> str:
        if not self.ready:
            return WAITING
        last_party = self.state["last_party"]
        if last_party and now - last_party < 600:
            return CELEBRATION
        if self.remaining <= 10:
            return FINAL
        if self.remaining <= self.ping_threshold:
            return CLOSE
        if self.progress >= self.goal / 2:
            return MOMENTUM
        return NORMAL

    # ── feeding readings in ───────────────────────────────────────────────────
    def apply(self, readings: dict[str, int | None], now: float) -> ApplyResult:
        result = ApplyResult()
        counts, pending = self.state["counts"], self.state["pending"]
        self.state["checked"] = now

        for site in self.sites:
            new = readings.get(site)
            if new is None:
                continue
            prev = counts.get(site)
            if prev is not None and new < prev:
                result.rejected[site] = f"went backwards ({prev} -> {new})"
                continue
            if prev is not None and new - prev > self.max_jump and pending.get(site) != new:
                pending[site] = new  # needs a second matching reading before we trust it
                result.rejected[site] = f"jump of {new - prev}, waiting for confirmation"
                continue
            pending.pop(site, None)
            counts[site] = new
            self.state["last_ok"][site] = now
            result.accepted.append(site)

        if self.state["baseline"] is None and all(s in counts for s in self.sites):
            self.state["baseline"] = self.total
            self.state["cycle_started"] = now
            log.info("first full reading: baseline set to %s", self.total)

        if self.ready:
            if self.total < self.state["baseline"]:  # only possible after a manual mistake
                self.state["baseline"] = self.total
            if self.progress >= self.goal:
                cycles = self.progress // self.goal
                self.state["parties"].append({"cycle": self.state["cycle"], "at": now, "total": self.total})
                self.state["parties"] = self.state["parties"][-25:]
                self.state["baseline"] += cycles * self.goal  # votes past the goal carry over
                self.state["cycle"] += 1
                self.state["cycle_started"] = now
                self.state["last_party"] = now
                self.state["ping_sent"] = False
                result.completed = True
            if 0 < self.remaining <= self.ping_threshold and not self.state["ping_sent"]:
                result.should_ping = True
        return result

    def mark_pinged(self) -> None:
        self.state["ping_sent"] = True

    # ── admin tools ───────────────────────────────────────────────────────────
    def set_remaining(self, remaining: int, now: float) -> bool:
        """Make the tracker show `remaining` votes to go. Needs every site read at least once."""
        if not all(s in self.state["counts"] for s in self.sites):
            return False
        remaining = min(max(remaining, 0), self.goal)
        self.state["baseline"] = self.total - (self.goal - remaining)
        self.state["cycle_started"] = self.state["cycle_started"] or now
        self.state["ping_sent"] = remaining <= self.ping_threshold and remaining > 0
        return True

    def rebase(self, now: float) -> bool:
        return self.set_remaining(self.goal, now)


def try_claim(player: dict, cycle: int, now: float, max_claims: int, cooldown: int) -> tuple[bool, str, int]:
    """Handle the 'I voted' button. Returns (ok, reason, seconds_until_next_allowed)."""
    if player.get("cycle") != cycle:
        player["cycle"] = cycle
        player["claims_cycle"] = 0
    if player["claims_cycle"] >= max_claims:
        return False, "limit", 0
    last = player.get("last_claim")
    if last is not None and last + cooldown > now:
        return False, "cooldown", int(last + cooldown - now) + 1
    player["claims_cycle"] += 1
    player["claims_total"] = player.get("claims_total", 0) + 1
    player["last_claim"] = now
    return True, "ok", 0
