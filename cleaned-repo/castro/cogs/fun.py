import random

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.i18n import FUN_FACTS, t
from core.ui import embed, reply


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="funfact", description=f"A fun fact about {cfg.NATION_NAME}")
    async def funfact(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.user.id)
        await reply(interaction, embed=embed(f"{cfg.NATION_FLAG} {cfg.NATION_NAME}", random.choice(FUN_FACTS[lang]), cfg.RED))

    @app_commands.command(name="language", description="Choose English or Español")
    @app_commands.choices(language=[app_commands.Choice(name="English", value="en"),
                                    app_commands.Choice(name="Español", value="es")])
    async def language(self, interaction: discord.Interaction, language: app_commands.Choice[str]):
        self.bot.store.data("users", {}).setdefault(str(interaction.user.id), {})["lang"] = language.value
        self.bot.store.save("users")
        await reply(interaction, t("lang_set", language.value))


async def setup(bot):
    await bot.add_cog(Fun(bot))
