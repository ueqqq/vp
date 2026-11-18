"""Rotating bot status (the 'Watching over Cuba 🇨🇺' line), editable from /castro settings."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands, tasks

from core.schema import parse_presence, render_template
from core.ui import ident

log = logging.getLogger("castro.status")
TYPES = {
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "playing": discord.ActivityType.playing,
    "competing": discord.ActivityType.competing,
}


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0

    async def cog_load(self):
        self.rotate.start()

    async def cog_unload(self):
        self.rotate.cancel()

    async def apply(self) -> None:
        gid = self.bot.primary_guild_id()
        if gid is None or not self.bot.settings.get(gid, "presence_enabled"):
            return
        lines = parse_presence(self.bot.settings.get(gid, "presence_lines"))
        if not lines:
            return
        verb, text = lines[self.index % len(lines)]
        self.index += 1
        i = ident(gid)
        text = render_template(text, nation=i.name, flag=i.flag)[:120]
        await self.bot.change_presence(activity=discord.Activity(type=TYPES[verb], name=text))

    @tasks.loop(minutes=10)
    async def rotate(self):
        try:
            await self.apply()
        except Exception:
            log.exception("status rotation failed")

    @rotate.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener("on_castro_setting_changed")
    async def _on_setting(self, guild_id: int, key: str):
        if key.startswith("presence") or key in ("nation_name", "nation_flag"):
            self.index = 0
            try:
                await self.apply()
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(Status(bot))
