"""Every admin-tunable setting, defined once: type, bounds, default and help text.

No Discord in here, so all validation is unit-tested. Adding a setting means adding one line to
SETTINGS; the /castro settings panel, /castro set and the validation pick it up automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from core import config as cfg

# theme -> (primary, accent). "bandera" matches the look the bot shipped with.
THEMES = {
    "bandera": (cfg.BLUE, cfg.RED),      # flag blue, flag red
    "roja": (cfg.RED, cfg.BLUE),         # flag red first
    "palma": (0x1E8449, cfg.GOLD),       # royal-palm green
    "dorada": (cfg.GOLD, cfg.RED),       # gold
}
PRESENCE_VERBS = ("watching", "listening", "playing", "competing")

TRUE_WORDS = {"on", "true", "yes", "y", "1", "si", "sí", "activado", "enabled"}
FALSE_WORDS = {"off", "false", "no", "n", "0", "desactivado", "disabled"}

GROUPS = {
    "identity": "🇨🇺 Identity & look",
    "votes": "🗳️ Vote party",
    "welcome": "👋 Welcome & support",
    "culture": "📜 Quotes & culture",
    "government": "🏛️ Government",
    "modules": "🧩 Features on/off",
    "status": "🎶 Bot status",
}

DEFAULT_WELCOME = (
    "Welcome to {nation}, **{name}**!\n\n"
    "Comrade, you have reached our shores. Whether you come to build a home, "
    "stand alongside our people, or speak on behalf of another nation, there is a place for you here.\n\n"
    "A nation is built by its people — and every great undertaking begins with someone willing to lay the first block.\n\n"
    "Read our rules, meet the community, and request citizenship if you wish to call {nation} home.\n"
    "Diplomats, our Foreign Affairs office awaits you.\n\n"
    "**¡Bienvenido a {nation}!** — Castro"
)
DEFAULT_SUPPORT = (
    "Need help from leadership or staff?\n"
    "Open a **private ticket** and we will get back to you.\n\n"
    "Want to serve the nation?\n"
    "**Apply for government** — applications are reviewed privately."
)
DEFAULT_PRESENCE = (
    "watching: over {nation} {flag}\n"
    "listening: son cubano 🎶\n"
    "playing: dominó\n"
    "watching: el cafecito ☕"
)


@dataclass(frozen=True)
class Setting:
    key: str
    group: str
    label: str
    kind: str  # int | bool | text | template | color | timezone | choice | lines
    default: Any
    help: str = ""
    min: int | None = None
    max: int | None = None
    choices: tuple[str, ...] = ()
    max_len: int = 200
    placeholders: tuple[str, ...] = ()
    allow_empty: bool = False


def _mod(key: str, label: str, help: str) -> Setting:
    return Setting(key, "modules", label, "bool", True, help)


SETTINGS: list[Setting] = [
    # identity
    Setting("nation_name", "identity", "Nation name", "text", cfg.NATION_NAME, "Used in titles, footers and messages.", max_len=40),
    Setting("nation_flag", "identity", "Flag emoji", "text", cfg.NATION_FLAG, "Shown beside the nation name.", max_len=12),
    Setting("motto", "identity", "Motto", "text", "", "Optional line shown on the nation directory.", max_len=100, allow_empty=True),
    Setting("theme", "identity", "Color theme", "choice", "bandera", "bandera (flag blue), roja (red), palma (green), dorada (gold).", choices=tuple(THEMES)),
    Setting("accent_color", "identity", "Custom main color", "color", "", "Hex like #002A8F. Leave empty to use the theme.", allow_empty=True),
    Setting("default_language", "identity", "Default language", "choice", "en", "For people who haven't picked one with /language.", choices=("en", "es")),
    # vote party
    Setting("vote_goal", "votes", "Votes per party", "int", cfg.VOTE_GOAL, "Votes needed for each vote party.", min=10, max=5000),
    Setting("ping_threshold", "votes", "Ping when this close", "int", cfg.PING_THRESHOLD, "Ping the VP role once this many votes remain.", min=1, max=500),
    Setting("poll_interval", "votes", "Check every (seconds)", "int", cfg.SCRAPE_INTERVAL, "Normal polling speed of the vote sites.", min=10, max=600),
    Setting("fast_interval", "votes", "Check every (seconds) when close", "int", cfg.FAST_INTERVAL, "Polling speed once a party is close.", min=10, max=300),
    Setting("claims_per_cycle", "votes", "'I voted' claims per cycle", "int", cfg.MAX_CLAIMS_PER_CYCLE, "How many times one player can claim per cycle.", min=1, max=20),
    Setting("claim_cooldown_min", "votes", "Minutes between claims", "int", cfg.CLAIM_COOLDOWN // 60, "Minimum gap between one player's claims.", min=1, max=720),
    Setting("ping_delete_minutes", "votes", "Delete pings after (min)", "int", cfg.PING_DELETE_SECONDS // 60, "Vote-party pings clean themselves up.", min=1, max=120),
    Setting("ping_message", "votes", "Ping message", "template",
            "{role} 🚨 ¡Ya casi! The vote party is close: only **{remaining}** votes to go!",
            "Placeholders: {role} {remaining} {nation} {flag}", max_len=300, placeholders=("role", "remaining", "nation", "flag")),
    Setting("celebration_message", "votes", "Party message", "template",
            "🎉 {flag} **¡Fiesta! Vote party time!** Thank you to everyone who voted.",
            "Placeholders: {nation} {flag}", max_len=300, placeholders=("nation", "flag")),
    # welcome & support
    Setting("welcome_title", "welcome", "Welcome title", "template", "{flag} ¡Bienvenido a {nation}!",
            "Placeholders: {name} {nation} {flag} {server}", max_len=100, placeholders=("name", "nation", "flag", "server")),
    Setting("welcome_message", "welcome", "Welcome message", "template", DEFAULT_WELCOME,
            "Placeholders: {name} {mention} {nation} {flag} {server}", max_len=1800, placeholders=("name", "mention", "nation", "flag", "server")),
    Setting("support_message", "welcome", "Support panel text", "template", DEFAULT_SUPPORT,
            "Placeholders: {nation} {flag}", max_len=800, placeholders=("nation", "flag")),
    # culture
    Setting("quote_hour", "culture", "Quote hour (0-23)", "int", cfg.QUOTE_HOUR, "Local hour the daily quote posts.", min=0, max=23),
    Setting("quote_timezone", "culture", "Quote timezone", "timezone", cfg.QUOTE_TZ, "e.g. America/Havana, America/Chicago, UTC.", max_len=60),
    Setting("daily_word", "culture", "Daily Cuban word", "bool", False, "Also post a 'palabra del día' with the quote."),
    # government
    Setting("poll_default_hours", "government", "Default poll length (hours)", "int", 24, "Pre-filled when leadership creates a poll.", min=1, max=168),
    Setting("poll_citizens_only", "government", "Polls are citizens-only", "bool", True, "Needs a configured Citizen role to take effect."),
    # modules
    _mod("module_votes", "Vote party", "Turn the vote tracker on or off."),
    _mod("module_quotes", "Quote of the day", "Turn daily quotes and /quote on or off."),
    _mod("module_music", "Music player", "Turn /play and friends on or off."),
    _mod("module_welcome", "Welcome messages", "Turn welcome messages on or off."),
    _mod("module_tickets", "Support tickets", "Turn ticket creation on or off."),
    # status
    Setting("presence_enabled", "status", "Rotate bot status", "bool", True, "Cycle through the status lines below."),
    Setting("presence_lines", "status", "Status lines", "lines", DEFAULT_PRESENCE,
            "One per line, optionally 'watching:', 'listening:', 'playing:' or 'competing:' first.", max_len=500),
]
BY_KEY = {s.key: s for s in SETTINGS}


# ── parsing ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Identity:
    name: str
    flag: str
    motto: str
    primary: int
    accent: int


def _token_names(text: str) -> set[str]:
    return set(re.findall(r"\{(\w*)\}", text))


def render_template(text: str, **values: Any) -> str:
    """Replace {name} placeholders; unknown ones are left untouched so a typo never crashes a message."""
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), text)


def parse_presence(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        verb, _, rest = line.partition(":")
        if rest and verb.strip().lower() in PRESENCE_VERBS:
            out.append((verb.strip().lower(), rest.strip()))
        else:
            out.append(("watching", line))
    return out


def resolve_color(theme: str, custom_hex: str) -> tuple[int, int]:
    primary, accent = THEMES.get(theme, THEMES["bandera"])
    if custom_hex and re.fullmatch(r"#[0-9a-fA-F]{6}", custom_hex):
        primary = int(custom_hex[1:], 16)
    return primary, accent


def parse(setting: Setting, raw: str) -> tuple[Any, str | None]:
    """Validate raw text for a setting. Returns (value, None) or (None, error message)."""
    raw = raw.strip()
    kind = setting.kind
    if not raw and not setting.allow_empty:
        return None, "This can't be empty."
    if kind == "int":
        try:
            value = int(raw)
        except ValueError:
            return None, "Enter a whole number."
        if setting.min is not None and value < setting.min or setting.max is not None and value > setting.max:
            return None, f"Must be between {setting.min} and {setting.max}."
        return value, None
    if kind == "bool":
        word = raw.lower()
        if word in TRUE_WORDS:
            return True, None
        if word in FALSE_WORDS:
            return False, None
        return None, "Enter on/off (or yes/no, sí/no)."
    if kind == "choice":
        word = raw.lower()
        if word not in setting.choices:
            return None, "Choose one of: " + ", ".join(setting.choices) + "."
        return word, None
    if kind == "color":
        if not raw:
            return "", None
        if not raw.startswith("#"):
            raw = "#" + raw
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
            return None, "Use a 6-digit hex color like #002A8F."
        return raw.upper(), None
    if kind == "timezone":
        try:
            ZoneInfo(raw)
        except Exception:
            return None, "Unknown timezone. Try something like America/Havana or UTC."
        return raw, None
    if kind == "lines":
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not 1 <= len(lines) <= 8:
            return None, "Give between 1 and 8 lines."
        if any(len(parse_presence(ln)[0][1]) > 60 for ln in lines):
            return None, "Each status line must be 60 characters or fewer."
        return "\n".join(lines), None
    # text / template
    if len(raw) > setting.max_len:
        return None, f"Too long: {len(raw)}/{setting.max_len} characters."
    if kind == "template":
        unknown = _token_names(raw) - set(setting.placeholders)
        if unknown:
            shown = ", ".join("{" + u + "}" for u in sorted(unknown))
            allowed = ", ".join("{" + p + "}" for p in setting.placeholders)
            return None, f"Unknown placeholder {shown}. You can use: {allowed}."
    return raw, None


def display_value(setting: Setting, value: Any, limit: int = 110) -> str:
    """Short, readable form of a value for the settings panel."""
    if setting.kind == "bool":
        return "✅ on" if value else "❌ off"
    text = str(value)
    if setting.kind == "lines":
        text = " / ".join(text.splitlines())
    elif setting.kind == "template":
        text = " ".join(text.split())
    if not text:
        return "—"
    return text if len(text) <= limit else text[: limit - 1] + "…"


class SettingValues:
    """Reads and writes setting values inside the shared Store, per server."""

    def __init__(self, store):
        self.store = store

    def _values(self, guild_id: int) -> dict:
        root = self.store.data("settings", {})
        guild = root.setdefault(str(guild_id), {"channels": {}, "roles": {}})
        guild.setdefault("channels", {})
        guild.setdefault("roles", {})
        return guild.setdefault("values", {})

    def get(self, guild_id: int, key: str) -> Any:
        return self._values(guild_id).get(key, BY_KEY[key].default)

    def is_default(self, guild_id: int, key: str) -> bool:
        return key not in self._values(guild_id)

    def set(self, guild_id: int, key: str, raw: str) -> tuple[bool, str]:
        setting = BY_KEY.get(key)
        if setting is None:
            return False, "Unknown setting."
        value, error = parse(setting, raw)
        if error:
            return False, error
        self._values(guild_id)[key] = value
        self.store.save("settings")
        return True, "Saved."

    def reset(self, guild_id: int, key: str) -> bool:
        removed = self._values(guild_id).pop(key, None) is not None
        self.store.save("settings")
        return removed
