"""Citizen profiles and the roster."""

from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.paginate import paginate
from core.ui import embed, leadership_only, reply, stamp

IGN_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
PER_PAGE = 15


class Pager(discord.ui.View):
    """Prev/next buttons over pre-built pages. Short-lived; roster pages are cheap to regenerate."""

    def __init__(self, title: str, pages: list[list[str]], total: int):
        super().__init__(timeout=180)
        self.title, self.pages, self.total, self.index = title, pages, total, 0
        self._sync()

    def _sync(self) -> None:
        self.prev.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.pages) - 1

    def render(self) -> discord.Embed:
        em = embed(self.title, "\n".join(self.pages[self.index]), cfg.BLUE)
        em.set_footer(text=f"Page {self.index + 1}/{len(self.pages)} · {self.total} total")
        return em

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        self._sync()
        await interaction.response.edit_message(embed=self.render(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(len(self.pages) - 1, self.index + 1)
        self._sync()
        await interaction.response.edit_message(embed=self.render(), view=self)


class Citizens(commands.Cog):
    profile = app_commands.Group(name="profile", description="Citizen profiles", guild_only=True)

    def __init__(self, bot):
        self.bot = bot

    def record(self, user_id: int) -> dict:
        return self.bot.store.data("players", {}).setdefault(str(user_id), {})

    @profile.command(name="view", description="View a citizen's profile")
    @app_commands.describe(member="Who to look up (defaults to you)")
    async def view(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        rec = self.bot.store.data("players", {}).get(str(member.id), {})
        is_citizen = self.bot.settings.has_role(member, "citizen")
        em = embed(f"{cfg.NATION_FLAG} {member.display_name}", rec.get("bio") or None, cfg.BLUE)
        em.set_thumbnail(url=member.display_avatar.url)
        em.add_field(name="Minecraft name", value=f"`{rec['ign']}`" if rec.get("ign") else "not linked")
        em.add_field(name="Town", value=rec.get("town") or "—")
        status = "Citizen" if is_citizen else "Not a citizen"
        if rec.get("citizen_since"):
            status += f" since {stamp(rec['citizen_since'], 'D')}"
        em.add_field(name="Status", value=status)
        em.add_field(name="Vote claims", value=str(rec.get("claims_total", 0)))
        if member.joined_at:
            em.add_field(name="In the server since", value=stamp(member.joined_at.timestamp(), "D"))
        await reply(interaction, embed=em)

    @profile.command(name="edit", description="Set your own town and bio")
    @app_commands.describe(town="Your town (max 40 chars)", bio="A short bio (max 200 chars)")
    async def edit(self, interaction: discord.Interaction, town: str | None = None, bio: str | None = None):
        if town is None and bio is None:
            return await reply(interaction, "Give a `town`, a `bio`, or both. (Link your Minecraft name with `/link`.)")
        if (town and len(town) > 40) or (bio and len(bio) > 200):
            return await reply(interaction, "❌ Town must be 40 characters or fewer and bio 200 or fewer.")
        rec = self.record(interaction.user.id)
        if town is not None:
            rec["town"] = town.strip()
        if bio is not None:
            rec["bio"] = bio.strip()
        self.bot.store.save("players")
        await reply(interaction, "✅ Profile updated.")

    @profile.command(name="fix", description="Correct a citizen's record (leadership)")
    @app_commands.describe(member="Whose record", ign="Correct Minecraft name", town="Correct town")
    @leadership_only()
    async def fix(self, interaction: discord.Interaction, member: discord.Member,
                  ign: str | None = None, town: str | None = None):
        if ign is not None and not IGN_RE.match(ign):
            return await reply(interaction, "❌ That isn't a valid Minecraft username.")
        rec = self.record(member.id)
        if ign is not None:
            rec["ign"] = ign
        if town is not None:
            rec["town"] = town.strip()[:40]
        self.bot.store.save("players")
        await reply(interaction, f"✅ Updated {member.display_name}'s record.")

    @app_commands.command(name="roster", description="List the nation's citizens")
    @app_commands.guild_only()
    async def roster(self, interaction: discord.Interaction):
        role = self.bot.settings.role(interaction.guild, "citizen")
        if role is None:
            return await reply(interaction, "❌ No citizen role is configured yet (`/castro setrole`).")
        players = self.bot.store.data("players", {})
        rows = []
        for m in sorted(role.members, key=lambda x: x.display_name.lower()):
            rec = players.get(str(m.id), {})
            line = f"**{discord.utils.escape_markdown(m.display_name)}**"
            if rec.get("ign"):
                line += f" · `{rec['ign']}`"
            if rec.get("town"):
                line += f" · {rec['town']}"
            rows.append(line)
        pages = paginate(rows, PER_PAGE)
        if not pages:
            return await reply(interaction, "No citizens yet.")
        view = Pager(f"{cfg.NATION_FLAG} Citizens of {cfg.NATION_NAME}", pages, len(rows))
        await reply(interaction, embed=view.render(), view=view)


async def setup(bot):
    await bot.add_cog(Citizens(bot))
