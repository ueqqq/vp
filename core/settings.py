"""Per-server channel/role configuration, set from Discord with /castro setchannel and /castro setrole."""

from __future__ import annotations

import discord

from core import config as cfg
from core.schema import Identity, SettingValues, resolve_color
from core.store import Store

CHANNEL_KINDS = {
    "welcome": "Welcome messages",
    "quotes": "Quote of the day",
    "votes": "Vote party tracker",
    "applications": "Where leadership reviews applications",
    "decrees": "Decrees",
    "treaties": "Treaty register",
    "logs": "Ticket / audit log",
    "ticket_category": "Category new tickets are created under",
}
ROLE_KINDS = {
    "staff": "Staff (handles tickets)",
    "leadership": "Leadership (reviews applications)",
    "citizen": "Citizen (granted on citizenship approval)",
    "ally": "Ally (granted on ally approval)",
    "vp": "Vote party ping role",
}


class Settings:
    def __init__(self, store: Store):
        self.store = store
        self.values = SettingValues(store)

    def _guild(self, guild_id: int) -> dict:
        everything = self.store.data("settings", {})
        guild = everything.setdefault(str(guild_id), {"channels": {}, "roles": {}})
        guild.setdefault("channels", {})
        guild.setdefault("roles", {})
        return guild

    # ── tunable values (see core/schema.py) ───────────────────────────────────
    def get(self, guild_id: int | None, key: str):
        from core.schema import BY_KEY
        return self.values.get(guild_id, key) if guild_id else BY_KEY[key].default

    def set(self, guild_id: int, key: str, raw: str) -> tuple[bool, str]:
        return self.values.set(guild_id, key, raw)

    def reset(self, guild_id: int, key: str) -> bool:
        return self.values.reset(guild_id, key)

    def enabled(self, guild_id: int | None, module: str) -> bool:
        return bool(self.get(guild_id, f"module_{module}"))

    def identity(self, guild_id: int | None) -> Identity:
        primary, accent = resolve_color(self.get(guild_id, "theme"), self.get(guild_id, "accent_color"))
        return Identity(self.get(guild_id, "nation_name"), self.get(guild_id, "nation_flag"),
                        self.get(guild_id, "motto"), primary, accent)

    def set_channel(self, guild_id: int, kind: str, channel_id: int) -> None:
        self._guild(guild_id)["channels"][kind] = channel_id
        self.store.save("settings")

    def set_role(self, guild_id: int, kind: str, role_id: int) -> None:
        self._guild(guild_id)["roles"][kind] = role_id
        self.store.save("settings")

    def channel(self, guild: discord.Guild, kind: str):
        channel_id = self._guild(guild.id)["channels"].get(kind)
        return guild.get_channel(channel_id) if channel_id else None

    def role(self, guild: discord.Guild, kind: str) -> discord.Role | None:
        role_id = self._guild(guild.id)["roles"].get(kind)
        if role_id:
            found = guild.get_role(role_id)
            if found:
                return found
        return discord.utils.get(guild.roles, name=cfg.ROLE_NAMES[kind])

    # ── permission helpers ────────────────────────────────────────────────────
    def is_admin(self, member: discord.abc.User) -> bool:
        return isinstance(member, discord.Member) and member.guild_permissions.administrator

    def has_role(self, member: discord.abc.User, kind: str) -> bool:
        if not isinstance(member, discord.Member):
            return False
        role = self.role(member.guild, kind)
        return bool(role and role in member.roles)

    def is_leadership(self, member: discord.abc.User) -> bool:
        return self.is_admin(member) or self.has_role(member, "leadership")

    def is_staff(self, member: discord.abc.User) -> bool:
        return self.is_leadership(member) or self.has_role(member, "staff")
