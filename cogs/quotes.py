"""Quote of the day.

Every quote needs an author and a source link. The seed quotes below came from your existing
#quote-of-the-day posts; they have no source URLs yet, so add them with /quote add and remove the
originals with /quote remove once you've verified each one.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core import config as cfg
from core.ui import ModuleDisabled, embed, ident, reply, staff_only

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

log = logging.getLogger("castro.quotes")

SEED = [
    ("Weapons are no more powerful than ideas.", "English translation · excerpt · July 26, 2002", None),
    ("Without the memory of your sacrifices of yesterday, our dreams of today would be impossible.", "English translation · excerpt · July 26, 2002", None),
    ("I believe ideas prevail over force.", "English translation · excerpt · Buenos Aires speech, 2003", None),
    ("Doctors, not bombs. Doctors, not smart weapons.", "English translation · excerpt · Buenos Aires speech, 2003", "https://en.granma.cu/cuba/2020-03-26/doctors-not-bombs"),
]


def _tz(name: str):
    try:
        return ZoneInfo(name)
    except Exception:
        log.warning("unknown timezone %r, falling back to UTC", name)
        return timezone.utc


class AddModal(discord.ui.Modal, title="Add a quote"):
    text = discord.ui.TextInput(label="Quote", style=discord.TextStyle.paragraph, max_length=500)
    author = discord.ui.TextInput(label="Who said it", default="Fidel Castro", max_length=80)
    note = discord.ui.TextInput(label="Context (translation, date, venue)", required=False, max_length=150)
    source = discord.ui.TextInput(label="Source link (required)", placeholder="https://…", max_length=300)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.source.value.strip().lower().startswith(("http://", "https://")):
            return await reply(interaction, "❌ The source must be a link starting with http:// or https://")
        cog = interaction.client.get_cog("Quotes")
        qid = cog.add(self.text.value.strip(), self.author.value.strip(), self.note.value.strip(), self.source.value.strip())
        await reply(interaction, f"✅ Quote **#{qid}** added.")


class Quotes(commands.Cog):
    quote = app_commands.Group(name="quote", description="Quote of the day", guild_only=True)

    def __init__(self, bot):
        self.bot = bot
        self.data = bot.store.data("quotes", {"next": 1, "items": [], "used": [], "last_id": None, "last_posted": None})
        if not self.data["items"] and self.data["next"] == 1:
            for text, note, source in SEED:
                self.add(text, "Fidel Castro", note, source)

    async def cog_load(self):
        self.tick.start()

    async def cog_unload(self):
        self.tick.cancel()

    def add(self, text: str, author: str, note: str, source: str | None) -> int:
        qid = self.data["next"]
        self.data["next"] += 1
        self.data["items"].append({"id": qid, "text": text, "author": author, "note": note, "source": source})
        self.bot.store.save("quotes")
        return qid

    def pick(self) -> dict | None:
        items = self.data["items"]
        if not items:
            return None
        fresh = [q for q in items if q["id"] not in self.data["used"]]
        if not fresh:  # everything has been shown once; start a new round
            self.data["used"] = []
            fresh = items
        return random.choice(fresh)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id and not self.bot.settings.enabled(interaction.guild_id, "quotes"):
            raise ModuleDisabled("Quotes are turned off on this server.")
        return True

    def _primary_guild(self):
        """The server that owns the daily schedule: the first one with a quotes channel set."""
        for guild in self.bot.guilds:
            if self.bot.settings.channel(guild, "quotes"):
                return guild
        return None

    def build(self, q: dict, guild_id: int | None = None) -> discord.Embed:
        i = ident(guild_id)
        # Format matching classic "Quote of the Day" style
        description = f"“{q['text']}”\n\n— **{q['author']}**"
        if q.get("note"):
            description += f"\n*{q['note']}*"
        if q.get("source"):
            description += f"\n\n[Source]({q['source']})"
        em = embed(f"{i.flag} Quote of the Day", description, i.accent)
        em.set_footer(text=f"{i.name} · Quote of the Day")
        return em


    async def post_today(self, force: bool = False) -> bool:
        q = self.pick()
        if q is None:
            return False
        sent = False
        for guild in self.bot.guilds:
            channel = self.bot.settings.channel(guild, "quotes")
            if channel is None:
                continue
            try:
                await channel.send(embed=self.build(q, guild.id))
                sent = True
                if self.bot.settings.get(guild.id, "daily_word"):
                    from cogs.cuba import word_embed
                    await channel.send(embed=word_embed(datetime.now(_tz(self.bot.settings.get(guild.id, "quote_timezone"))).date(),
                                                        self.bot.lang(0, guild.id), guild.id))
            except discord.HTTPException as exc:
                log.warning("could not post quote in %s: %s", guild.name, exc)
        if sent:
            self.data["used"].append(q["id"])
            self.data["last_id"] = q["id"]
            self.bot.store.save("quotes")
        return sent

    @tasks.loop(minutes=5)
    async def tick(self):
        try:
            guild = self._primary_guild()
            if guild is None or not self.bot.settings.enabled(guild.id, "quotes"):
                return
            now = datetime.now(_tz(self.bot.settings.get(guild.id, "quote_timezone")))
            today = now.date().isoformat()
            if self.data["last_posted"] == today:
                return
            hour = self.bot.settings.get(guild.id, "quote_hour")
            if not (hour <= now.hour < hour + 3):  # a short catch-up window after restarts
                return
            if await self.post_today():
                self.data["last_posted"] = today
                self.bot.store.save("quotes")
        except Exception:
            log.exception("quote tick failed")

    @tick.before_loop
    async def _before_tick(self):
        await self.bot.wait_until_ready()

    @quote.command(name="today", description="Show the latest quote of the day")
    async def today(self, interaction: discord.Interaction):
        q = next((x for x in self.data["items"] if x["id"] == self.data["last_id"]), None) or self.pick()
        if q is None:
            return await reply(interaction, "No quotes yet.")
        await reply(interaction, embed=self.build(q, interaction.guild_id))

    @quote.command(name="add", description="Add a quote (staff)")
    @staff_only()
    async def add_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddModal())

    @quote.command(name="remove", description="Remove a quote by id (staff)")
    @staff_only()
    async def remove(self, interaction: discord.Interaction, quote_id: int):
        before = len(self.data["items"])
        self.data["items"] = [q for q in self.data["items"] if q["id"] != quote_id]
        self.bot.store.save("quotes")
        await reply(interaction, "✅ Removed." if len(self.data["items"]) < before else "❌ No quote with that id.")

    @quote.command(name="list", description="List all quotes (staff)")
    @staff_only()
    async def list_cmd(self, interaction: discord.Interaction):
        rows = [f"`#{q['id']}` {q['text'][:70]}{'…' if len(q['text']) > 70 else ''} {'🔗' if q.get('source') else '⚠️ no source'}"
                for q in self.data["items"]]
        await reply(interaction, embed=embed(f"Quotes ({len(rows)})", "\n".join(rows)[:4000] or "None.", cfg.BLUE))

    @quote.command(name="post", description="Post a quote to the quotes channel right now (staff)")
    @staff_only()
    async def post_now(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ok = await self.post_today(force=True)
        await interaction.followup.send("✅ Posted." if ok else "❌ Nothing posted. Is a quotes channel set (`/castro setchannel`)?", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Quotes(bot))
