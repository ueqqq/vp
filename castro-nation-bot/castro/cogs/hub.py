"""The command hub panel, /help, and the official Cuba welcome message for new members."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.schema import render_template
from core.ui import embed, ident, reply


def help_embed(guild_id: int | None = None) -> discord.Embed:
    i = ident(guild_id)
    em = embed(f"{i.flag} Castro — Command Guide", color=i.primary)
    em.description = (
        f"Tools for **{i.name}**. Most replies are private so the chat stays clean.\n\n"
        "**For everyone**\n"
        "• `/help` — this guide\n"
        "• `/nation` — directory, towns, government, relations\n"
        "• `/quote today` — today's Quote of the Day\n"
        "• `/cuba` — facts, slang, food and music (`fact` `slang` `dish` `music` `word`)\n"
        "• `/profile` `/roster` `/decree list` `/poll results` `/treaty list`\n"
        "• Music: `/play` `/skip` `/queue` `/nowplaying` `/stop` `/pause` `/resume`\n\n"
        "**Citizenship & support**\n"
        "• Request citizenship or open a ticket from the panels / welcome buttons\n\n"
        "**Leadership**\n"
        "• `/decree` `/poll` `/treaty` `/nation edit` and more\n\n"
        "**Staff / Admin**\n"
        "• `/quote add|remove|list|post`\n"
        "• `/castro settings` — change almost everything from one panel\n"
        "• `/castro setchannel` `/castro setrole` `/castro panel` `/castro status` `/castro preview`"
    )
    em.set_footer(text=f"Castro v{cfg.VERSION} · {i.name}")
    return em


class HubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for label, url in cfg.LINKS.items():
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))

    @discord.ui.button(label="Help", emoji="❓", style=discord.ButtonStyle.primary, custom_id="castro:hub:help")
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=help_embed(interaction.guild_id))

    @discord.ui.button(label="Nation directory", style=discord.ButtonStyle.primary, custom_id="castro:hub:directory")
    async def directory(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=interaction.client.get_cog("Nation").overview_embed(interaction.guild_id))

    @discord.ui.button(label="Citizenship", style=discord.ButtonStyle.success, custom_id="castro:hub:citizenship")
    async def citizenship(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.applications import ApplicationModal
        await interaction.response.send_modal(ApplicationModal("citizenship"))


class WelcomeView(discord.ui.View):
    """Buttons under the official welcome message."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Citizenship", emoji="🇨🇺", style=discord.ButtonStyle.success,
                       custom_id="castro:welcome:citizen")
    async def citizen(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.applications import ApplicationModal
        await interaction.response.send_modal(ApplicationModal("citizenship"))

    @discord.ui.button(label="Open Ticket", emoji="🎫", style=discord.ButtonStyle.primary,
                       custom_id="castro:welcome:ticket")
    async def ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.support import TicketModal
        await interaction.response.send_modal(TicketModal())

    @discord.ui.button(label="Foreign Affairs", emoji="🕊️", style=discord.ButtonStyle.secondary,
                       custom_id="castro:welcome:diplomacy")
    async def diplomacy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(
            interaction,
            "Diplomats: please open a ticket or contact leadership in the **Foreign Affairs** channel. "
            "You can also use the Nation Support panel.",
        )


def build_welcome_embed(member: discord.Member, settings) -> discord.Embed:
    """The welcome message. Title and body are templates editable in /castro settings."""
    gid = member.guild.id
    i = ident(gid)
    values = dict(name=member.display_name, mention=member.mention, nation=i.name, flag=i.flag, server=member.guild.name)
    em = discord.Embed(
        title=render_template(settings.get(gid, "welcome_title"), **values),
        description=render_template(settings.get(gid, "welcome_message"), **values),
        color=i.accent,
    )
    em.add_field(name="Citizenship", value="Button below · ⁠role-request", inline=True)
    em.add_field(name="Support", value="Open a ticket · ⁠tickets", inline=True)
    em.add_field(name="Diplomacy", value="Foreign Affairs · ⁠foreign-affairs", inline=True)
    em.set_thumbnail(url=member.display_avatar.url)
    em.set_footer(text=f"Member #{member.guild.member_count} · {i.name}")
    return em


class Hub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(HubView())
        self.bot.add_view(WelcomeView())

    async def post_panel(self, channel: discord.abc.Messageable) -> None:
        i = ident(getattr(getattr(channel, "guild", None), "id", None))
        await channel.send(
            embed=embed(f"{i.flag} Castro command hub",
                        "Use `/help` for tools, citizenship and more. Results are private by default.", i.primary),
            view=HubView(),
        )

    @app_commands.command(name="help", description="See what Castro can do")
    async def help_cmd(self, interaction: discord.Interaction):
        await reply(interaction, embed=help_embed(interaction.guild_id))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        if not self.bot.settings.enabled(member.guild.id, "welcome"):
            return
        channel = self.bot.settings.channel(member.guild, "welcome")
        if channel is None:
            return
        try:
            await channel.send(
                content=member.mention,
                embed=build_welcome_embed(member, self.bot.settings),
                view=WelcomeView(),
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Hub(bot))
