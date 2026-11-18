"""All settings in one place. Anything tunable can be overridden with an env var."""

from __future__ import annotations

import os
from pathlib import Path

try:  # .env support is optional; real env vars always win
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _int(name: str, default: int, minimum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        value = default
    return max(value, minimum) if minimum is not None else value


BOT_NAME = "Castro"
VERSION = "2.1.0"  # bump when slash commands change; triggers a one-time re-sync
NATION_NAME = "Cuba"
NATION_FLAG = "🇨🇺"

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID = _int("GUILD_ID", 0)  # optional: sync commands to one server instantly (dev)
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

# ── Vote party ────────────────────────────────────────────────────────────────
VOTE_GOAL = _int("VOTE_GOAL", 250, 1)
SCRAPE_INTERVAL = _int("SCRAPE_INTERVAL_SECONDS", 30, 10)  # normal polling
FAST_INTERVAL = min(_int("FAST_INTERVAL_SECONDS", 15, 10), SCRAPE_INTERVAL)  # used once the party is close
PING_THRESHOLD = _int("PING_THRESHOLD", 30, 1)
PING_DELETE_SECONDS = 300
MAX_CLAIMS_PER_CYCLE = 3
CLAIM_COOLDOWN = 3600
REMINDER_DELAY = 1800
STALE_AFTER = 900  # a site not read for 15 min is shown as stale
MAX_JUMP = 500  # a bigger single-scrape jump must be seen twice before it is trusted

VOTE_SITES = [
    {
        "name": "Minecraft-MP",
        "url": "https://minecraft-mp.com/server-s349345",
        "vote_url": "https://minecraft-mp.com/server-s349345/vote/",
        "emoji": "🟡",
        "cloudflare": False,
        "patterns": [
            r"Vote\(s\)</strong>\s*</td>\s*<td[^>]*>\s*(\d[\d,]*)",
            r"Vote\(s\)[^0-9]{0,50}(\d[\d,]*)",
        ],
    },
    {
        "name": "MinecraftServers.org",
        "url": "https://minecraftservers.org/server/679302",
        "vote_url": "https://minecraftservers.org/vote/679302",
        "emoji": "🔵",
        "cloudflare": False,
        "patterns": [
            r">Votes</div>\s*<div[^>]*>\s*(\d[\d,]*)\s*</div>",
            r"Votes\s*</div>\s*<div[^>]*>\s*(\d[\d,]*)\s*</div>",
        ],
    },
    {
        "name": "Minecraft-Server-List",
        "url": "https://minecraft-server-list.com/server/513054/vote/",
        "vote_url": "https://minecraft-server-list.com/server/513054/vote/",
        "emoji": "🔴",
        "cloudflare": True,  # sits behind Cloudflare; fetched with cloudscraper in a thread
        "patterns": [
            r"(\d[\d,]*)\s+Players have voted",
            r"<b>(\d[\d,]*)\s+Votes\s*-\s*All time</b>",
        ],
    },
]

# ── Quote of the day ──────────────────────────────────────────────────────────
QUOTE_TZ = os.getenv("QUOTE_TZ", "UTC")  # e.g. America/Chicago
QUOTE_HOUR = _int("QUOTE_HOUR", 8, 0)

# ── Roles are matched by name unless overridden with /castro setrole ──────────
ROLE_NAMES = {
    "staff": "Staff",
    "leadership": "Leadership",
    "citizen": "Nation Member",
    "ally": "Ally",
    "vp": "VP",
}

LINKS = {
    "Live map": "https://map.diplomaticamc.com",
    "Live market": "https://market.diplomaticamc.com",
}

# ── Colours ───────────────────────────────────────────────────────────────────
BLUE = 0x002A8F
RED = 0xCF142B
GREEN = 0x2ECC71
GOLD = 0xF1C40F
GREY = 0x95A5A6
