"""/castro: one-time server setup done from inside Discord (no editing code or config files)."""

from __future__ import annotations

import typing

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.settings import CHANNEL_KINDS, ROLE_KINDS
from core.ui import admin_only, embed, reply

PANELS = {"hub": "Command hub", "support": "Nation Support", "nation": "Nation directory", "votes": "Vote party tracker"}


class Admin(commands.Cog):
    castro = app_commands.Group(name="castro", description="Set up and manage Castro", guild_only=True,
                                default_permissions=discord.Permissions(administrator=True))

    def __init__(self, bot):
        self.bot = bot

    @castro.command(name="setchannel", description="Tell Castro which channel to use for something")
    @app_commands.describe(purpose="What the channel is for", channel="The channel (or category for tickets)")
    @app_commands.choices(purpose=[app_commands.Choice(name=v, value=k) for k, v in CHANNEL_KINDS.items()])
    @admin_only()
    async def setchannel(self, interaction: discord.Interaction, purpose: app_commands.Choice[str],
                         channel: typing.Union[discord.TextChannel, discord.CategoryChannel]):
        is_category = isinstance(channel, discord.CategoryChannel)
        if (purpose.value == "ticket_category") != is_category:
            return await reply(interaction, "❌ Tickets need a **category**; every other purpose needs a **text channel**.")
        self.bot.settings.set_channel(interaction.guild_id, purpose.value, channel.id)
        await reply(interaction, f"✅ {purpose.name} → {channel.mention}")

    @castro.command(name="setrole", description="Tell Castro which role to use (otherwise it matches by name)")
    @app_commands.choices(purpose=[app_commands.Choice(name=v, value=k) for k, v in ROLE_KINDS.items()])
    @admin_only()
    async def setrole(self, interaction: discord.Interaction, purpose: app_commands.Choice[str], role: discord.Role):
        self.bot.settings.set_role(interaction.guild_id, purpose.value, role.id)
        await reply(interaction, f"✅ {purpose.name} → {role.mention}", allowed_mentions=discord.AllowedMentions.none())

    @castro.command(name="panel", description="Post a panel in this channel")
    @app_commands.choices(kind=[app_commands.Choice(name=v, value=k) for k, v in PANELS.items()])
    @admin_only()
    async def panel(self, interaction: discord.Interaction, kind: app_commands.Choice[str]):
        cogs = {"hub": "Hub", "support": "Support", "nation": "Nation"}
        if kind.value == "votes":
            return await reply(interaction, "Use `/voteparty setup` for the vote tracker.")
        try:
            await self.bot.get_cog(cogs[kind.value]).post_panel(interaction.channel)
        except discord.Forbidden:
            return await reply(interaction, "❌ I can't post in this channel. Check my permissions.")
        await reply(interaction, f"✅ {kind.name} panel posted.")

    @castro.command(name="status", description="Check that everything is configured")
    @admin_only()
    async def status(self, interaction: discord.Interaction):
        s, g = self.bot.settings, interaction.guild
        chan = [f"{'✅' if (c := s.channel(g, k)) else '❌'} {label}: {c.mention if c else 'not set'}"
                for k, label in CHANNEL_KINDS.items()]
        role = [f"{'✅' if (r := s.role(g, k)) else '❌'} {label}: {r.mention if r else 'not found'}"
                for k, label in ROLE_KINDS.items()]
        em = embed(f"{cfg.NATION_FLAG} Castro setup checklist", color=cfg.BLUE)
        em.add_field(name="Channels (`/castro setchannel`)", value="\n".join(chan), inline=False)
        em.add_field(name="Roles (`/castro setrole`)", value="\n".join(role), inline=False)
        em.set_footer(text=f"Castro v{cfg.VERSION}")
        await reply(interaction, embed=em, allowed_mentions=discord.AllowedMentions.none())

    @castro.command(name="sync", description="Re-register slash commands with Discord")
    @admin_only()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.sync_commands()
        await interaction.followup.send(f"✅ Synced {synced} commands.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))
