"""/cuba: Cuban culture, in English and Spanish. Content lives in core/cuba.py."""

from __future__ import annotations

import datetime

import discord
from discord import app_commands
from discord.ext import commands

from core import cuba
from core.ui import embed, ident, reply


def _title(es: str, en: str, lang: str) -> str:
    return es if lang == "es" else en


def fact_embed(entry: dict, lang: str, guild_id: int | None) -> discord.Embed:
    i = ident(guild_id)
    return embed(f"{i.flag} {_title('Dato curioso', 'Did you know?', lang)}", entry[lang], i.accent)


def slang_embed(entry: dict, lang: str, guild_id: int | None, heading: str | None = None) -> discord.Embed:
    i = ident(guild_id)
    other = "en" if lang == "es" else "es"
    em = embed(f"🗣️ {entry['term']}", f"**{entry[lang]}**\n*{entry[other]}*", i.accent)
    em.add_field(name=_title("Ejemplo", "Example", lang), value=f"“{entry['example']}”", inline=False)
    em.set_footer(text=heading or _title("Español cubano · el uso varía según la región", "Cuban Spanish · usage varies by region", lang))
    return em


def word_embed(day: datetime.date, lang: str, guild_id: int | None) -> discord.Embed:
    return slang_embed(cuba.word_of_day(day), lang, guild_id,
                       _title("Palabra del día", "Word of the day", lang) + f" · {day.isoformat()}")


def dish_embed(entry: dict, lang: str, guild_id: int | None) -> discord.Embed:
    i = ident(guild_id)
    return embed(f"🍽️ {entry['name']}", entry[lang], i.primary)


def music_embed(entry: dict, lang: str, guild_id: int | None) -> discord.Embed:
    i = ident(guild_id)
    return embed(f"🎶 {entry['name']}", entry[lang], i.primary)


class CubaCog(commands.Cog, name="Cuba"):
    cuba_group = app_commands.Group(name="cuba", description="Cuban culture: facts, slang, food and music", guild_only=True)

    def __init__(self, bot):
        self.bot = bot

    def _lang(self, interaction: discord.Interaction) -> str:
        return self.bot.lang(interaction.user.id, interaction.guild_id)

    @cuba_group.command(name="fact", description="A random fact about Cuba")
    async def fact(self, interaction: discord.Interaction):
        await reply(interaction, embed=fact_embed(cuba.pick("fact"), self._lang(interaction), interaction.guild_id), ephemeral=False)

    @cuba_group.command(name="slang", description="Learn Cuban slang (leave empty for a random word)")
    @app_commands.describe(term="A word to look up, like asere or guagua")
    async def slang(self, interaction: discord.Interaction, term: str | None = None):
        lang = self._lang(interaction)
        if term:
            entry = cuba.find_slang(term)
            if entry is None:
                known = ", ".join(s["term"] for s in cuba.SLANG)
                return await reply(interaction, f"🤷 I don't have **{term}** yet. I know: {known}")
        else:
            entry = cuba.pick("slang")
        await reply(interaction, embed=slang_embed(entry, lang, interaction.guild_id), ephemeral=False)

    @slang.autocomplete("term")
    async def _slang_auto(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=s["term"], value=s["term"]) for s in cuba.SLANG
                if current in s["term"].lower()][:25]

    @cuba_group.command(name="word", description="Today's Cuban word of the day")
    async def word(self, interaction: discord.Interaction):
        await reply(interaction, embed=word_embed(datetime.date.today(), self._lang(interaction), interaction.guild_id), ephemeral=False)

    @cuba_group.command(name="dish", description="A classic Cuban dish")
    async def dish(self, interaction: discord.Interaction):
        await reply(interaction, embed=dish_embed(cuba.pick("dish"), self._lang(interaction), interaction.guild_id), ephemeral=False)

    @cuba_group.command(name="music", description="Cuban music, genres and artists")
    async def music(self, interaction: discord.Interaction):
        await reply(interaction, embed=music_embed(cuba.pick("music"), self._lang(interaction), interaction.guild_id), ephemeral=False)


async def setup(bot):
    await bot.add_cog(CubaCog(bot))
