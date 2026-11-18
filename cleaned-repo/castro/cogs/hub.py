"""The command hub panel and /help, plus the welcome message for new members."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.ui import embed, reply

HELP = [
    ("🗳️ Vote party", "`/link` · `/myvotes` · `/leaderboard`, plus the buttons on the tracker"),
    ("🧑 Citizens", "`/profile view` · `/profile edit` · `/roster`"),
    ("🏛️ Government", "`/decree list` · `/decree view` · `/poll results`; vote with the buttons on a poll"),
    ("🌐 Diplomacy", "`/treaty list` · `/treaty view` · `/nation view`"),
    ("📜 Quotes", "`/quote today` shows today's quote of the day"),
    ("🎫 Support", "Use the **Nation Support** panel to open a private ticket or apply for government"),
    ("🌍 Misc", "`/funfact` · `/language` (English / Español)"),
]


def help_embed() -> discord.Embed:
    em = embed(f"{cfg.NATION_FLAG} Castro command hub", "Everything's private to you unless noted. Here's what I can do:", cfg.BLUE)
    for name, value in HELP:
        em.add_field(name=name, value=value, inline=False)
    return em


class HubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for label, url in cfg.LINKS.items():
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))

    @discord.ui.button(label="Help", emoji="❓", style=discord.ButtonStyle.primary, custom_id="castro:hub:help")
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=help_embed())

    @discord.ui.button(label="Nation directory", style=discord.ButtonStyle.primary, custom_id="castro:hub:directory")
    async def directory(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=interaction.client.get_cog("Nation").overview_embed())

    @discord.ui.button(label="Citizenship", style=discord.ButtonStyle.primary, custom_id="castro:hub:citizenship")
    async def citizenship(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.applications import ApplicationModal
        await interaction.response.send_modal(ApplicationModal("citizenship"))


class Hub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(HubView())

    async def post_panel(self, channel: discord.abc.Messageable) -> None:
        await channel.send(embed=embed(f"{cfg.NATION_FLAG} Castro command hub",
                                       "Use `/help` for tools, news, citizenship and language preferences. "
                                       "Results are private by default.", cfg.BLUE), view=HubView())

    @app_commands.command(name="help", description="See what Castro can do")
    async def help(self, interaction: discord.Interaction):
        await reply(interaction, embed=help_embed())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        channel = self.bot.settings.channel(member.guild, "welcome")
        if channel is None:
            return
        em = embed(f"{cfg.NATION_FLAG} ¡Bienvenido, {member.display_name}!",
                   f"Welcome to **{cfg.NATION_NAME}**, {member.mention}! Request citizenship below, browse the "
                   "directory, or use `/help` to see everything I can do.", cfg.BLUE)
        try:
            await channel.send(embed=em, view=HubView(), allowed_mentions=discord.AllowedMentions(users=True))
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Hub(bot))
