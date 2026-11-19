"""/castro — server setup and control panel. Everything configurable from Discord."""

from __future__ import annotations

import typing

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.settings import CHANNEL_KINDS, ROLE_KINDS
from core.schema import BY_KEY, SETTINGS, display_value, render_template
from core.ui import admin_only, embed, ident, nation, reply, success


PANELS = {
    "hub": "Command Hub",
    "support": "Nation Support / Tickets",
    "nation": "Nation Directory",
    "votes": "Vote Party Tracker",
}


class Admin(commands.Cog):
    castro = app_commands.Group(
        name="castro",
        description="Set up and manage Castro for this server",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot):
        self.bot = bot

    @castro.command(name="setchannel", description="Assign a channel for a specific purpose")
    @app_commands.describe(
        purpose="What this channel is used for",
        channel="Text channel (or category when setting ticket category)",
    )
    @app_commands.choices(purpose=[app_commands.Choice(name=v, value=k) for k, v in CHANNEL_KINDS.items()])
    @admin_only()
    async def setchannel(
        self,
        interaction: discord.Interaction,
        purpose: app_commands.Choice[str],
        channel: typing.Union[discord.TextChannel, discord.CategoryChannel],
    ):
        is_category = isinstance(channel, discord.CategoryChannel)
        if purpose.value == "ticket_category" and not is_category:
            return await reply(interaction, embed=embed("❌ Wrong type", "Ticket category must be a **category**, not a text channel.", cfg.RED))
        if purpose.value != "ticket_category" and is_category:
            return await reply(interaction, embed=embed("❌ Wrong type", "This purpose needs a **text channel**.", cfg.RED))

        self.bot.settings.set_channel(interaction.guild_id, purpose.value, channel.id)
        await reply(
            interaction,
            embed=success("Channel set", f"**{purpose.name}** → {channel.mention}"),
        )

    @castro.command(name="setrole", description="Assign a role for a specific purpose")
    @app_commands.describe(purpose="What this role is used for", role="The Discord role")
    @app_commands.choices(purpose=[app_commands.Choice(name=v, value=k) for k, v in ROLE_KINDS.items()])
    @admin_only()
    async def setrole(self, interaction: discord.Interaction, purpose: app_commands.Choice[str], role: discord.Role):
        self.bot.settings.set_role(interaction.guild_id, purpose.value, role.id)
        await reply(
            interaction,
            embed=success("Role set", f"**{purpose.name}** → {role.mention}"),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @castro.command(name="panel", description="Post one of the permanent panels in this channel")
    @app_commands.describe(kind="Which panel to post")
    @app_commands.choices(kind=[app_commands.Choice(name=v, value=k) for k, v in PANELS.items()])
    @admin_only()
    async def panel(self, interaction: discord.Interaction, kind: app_commands.Choice[str]):
        if kind.value == "votes":
            return await reply(
                interaction,
                embed=embed("Vote tracker", "Use `/voteparty setup` to post and configure the live vote party tracker.", cfg.BLUE),
            )

        cog_map = {"hub": "Hub", "support": "Support", "nation": "Nation"}
        cog = self.bot.get_cog(cog_map[kind.value])
        if cog is None:
            return await reply(interaction, embed=embed("❌ Error", "That panel is unavailable right now.", cfg.RED))

        try:
            await cog.post_panel(interaction.channel)
        except discord.Forbidden:
            return await reply(
                interaction,
                embed=embed("❌ Missing permissions", "I need **Send Messages** and **Embed Links** in this channel.", cfg.RED),
            )
        await reply(interaction, embed=success("Panel posted", f"**{kind.name}** is now live in {interaction.channel.mention}."))

    @castro.command(name="status", description="Full setup checklist for this server")
    @admin_only()
    async def status(self, interaction: discord.Interaction):
        s, g = self.bot.settings, interaction.guild

        channels = []
        for key, label in CHANNEL_KINDS.items():
            ch = s.channel(g, key)
            channels.append(f"{'✅' if ch else '❌'} **{label}** — {ch.mention if ch else '*not set*'}")

        roles = []
        for key, label in ROLE_KINDS.items():
            r = s.role(g, key)
            roles.append(f"{'✅' if r else '❌'} **{label}** — {r.mention if r else '*not found*'}")

        em = nation("Castro Setup Checklist", guild_id=g.id)
        em.description = (
            f"Server: **{g.name}**\n"
            f"Version: `{cfg.VERSION}`\n\n"
            "Use the commands below to finish any missing pieces."
        )
        em.add_field(name="Channels  ·  `/castro setchannel`", value="\n".join(channels), inline=False)
        em.add_field(name="Roles  ·  `/castro setrole`", value="\n".join(roles), inline=False)
        modules = [f"{'✅' if s.enabled(g.id, m) else '❌'} {m}" for m in ("votes", "quotes", "music", "welcome", "tickets")]
        em.add_field(name="Features  ·  `/castro settings`", value="  ·  ".join(modules), inline=False)
        em.add_field(
            name="Quick start",
            value=(
                "1. Set **Welcome messages** → your immigrants channel\n"
                "2. Set **Quotes** → quote-of-the-day channel\n"
                "3. Set **Ticket category** + staff role\n"
                "4. Post panels with `/castro panel`"
            ),
            inline=False,
        )
        await reply(interaction, embed=em, allowed_mentions=discord.AllowedMentions.none())

    @castro.command(name="sync", description="Force re-register all slash commands with Discord")
    @admin_only()
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            count = await self.bot.sync_commands()
            await interaction.followup.send(embed=success("Commands synced", f"**{count}** commands registered."), ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(embed=embed("❌ Sync failed", str(exc), cfg.RED), ephemeral=True)

    # ── settings ──────────────────────────────────────────────────────────────
    @castro.command(name="settings", description="Open the settings panel: names, colors, messages, vote tuning, features")
    @admin_only()
    async def settings_panel(self, interaction: discord.Interaction):
        from cogs.settings_ui import SettingsView
        view = SettingsView(self.bot, interaction.user.id, interaction.guild_id)
        await reply(interaction, embed=view.render(), view=view)

    @castro.command(name="set", description="Change one setting directly")
    @app_commands.describe(setting="Which setting", value="New value")
    @admin_only()
    async def set_value(self, interaction: discord.Interaction, setting: str, value: str):
        if setting not in BY_KEY:
            return await reply(interaction, embed=embed("❌ Unknown setting", "Start typing to pick one from the list.", cfg.RED))
        ok, message = self.bot.settings.set(interaction.guild_id, setting, value)
        if not ok:
            return await reply(interaction, embed=embed(f"❌ {BY_KEY[setting].label}", message, cfg.RED))
        self.bot.setting_changed(interaction.guild_id, setting)
        shown = display_value(BY_KEY[setting], self.bot.settings.get(interaction.guild_id, setting))
        await reply(interaction, embed=success(f"{BY_KEY[setting].label}", f"**Now:** {shown}"))

    @castro.command(name="reset", description="Put a setting back to its default")
    @app_commands.describe(setting="Which setting")
    @admin_only()
    async def reset_value(self, interaction: discord.Interaction, setting: str):
        if setting not in BY_KEY:
            return await reply(interaction, embed=embed("❌ Unknown setting", "Start typing to pick one from the list.", cfg.RED))
        changed = self.bot.settings.reset(interaction.guild_id, setting)
        self.bot.setting_changed(interaction.guild_id, setting)
        await reply(interaction, embed=success(
            BY_KEY[setting].label,
            "Restored to the default." if changed else "It was already the default.",
        ))

    @set_value.autocomplete("setting")
    @reset_value.autocomplete("setting")
    async def _setting_names(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower().strip()
        # Discord only allows 25 choices. Prefer matches on key/label; if nothing typed,
        # return a stable alphabetical slice so every setting is still reachable by typing.
        matches = [s for s in SETTINGS if not current or current in s.key.lower() or current in s.label.lower()]
        matches.sort(key=lambda s: (s.group, s.label.lower()))
        return [app_commands.Choice(name=f"{s.label} ({s.key})"[:100], value=s.key) for s in matches[:25]]

    @castro.command(name="preview", description="See how a customizable message will look")
    @app_commands.describe(what="Which message to preview")
    @app_commands.choices(what=[
        app_commands.Choice(name="Welcome message", value="welcome"),
        app_commands.Choice(name="Support panel", value="support"),
        app_commands.Choice(name="Vote party ping", value="ping"),
        app_commands.Choice(name="Vote party celebration", value="party"),
    ])
    @admin_only()
    async def preview(self, interaction: discord.Interaction, what: app_commands.Choice[str]):
        gid, s, i = interaction.guild_id, self.bot.settings, ident(interaction.guild_id)
        if what.value == "welcome":
            from cogs.hub import build_welcome_embed
            return await reply(interaction, embed=build_welcome_embed(interaction.user, s))
        if what.value == "support":
            return await reply(interaction, embed=self.bot.get_cog("Support").panel_embed(gid))
        values = dict(role="@VP", remaining=12, nation=i.name, flag=i.flag)
        text = render_template(s.get(gid, "ping_message" if what.value == "ping" else "celebration_message"), **values)
        await reply(interaction, f"**Preview** (sample numbers):\n{text}", allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(Admin(bot))
