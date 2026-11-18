"""Nation directory.

This data is maintained by leadership with /nation commands. DiplomaticaMC has no official API
wired in here, so the embed says plainly that it is hand-maintained and shows when it was last
updated, rather than pretending to be live game data.
"""

from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.ui import embed, leadership_only, reply, stamp

RELATIONS = {"ally": "🤝 Ally", "friendly": "🙂 Friendly", "neutral": "😐 Neutral",
             "hostile": "😠 Hostile", "at_war": "⚔️ At war"}


def default_data() -> dict:
    return {"leader": "", "capital": "", "residents": "", "bank": "", "chunks": "", "updated": None,
            "towns": [], "government": {}, "relations": {}, "panel": {"channel": None, "message": None}}


class EditModal(discord.ui.Modal, title="Edit nation overview"):
    def __init__(self, data: dict):
        super().__init__()
        self.boxes = {}
        for key, label in (("leader", "Leader"), ("capital", "Capital"), ("residents", "Residents"),
                           ("bank", "Bank (e.g. 2g)"), ("chunks", "Claimed chunks")):
            box = discord.ui.TextInput(label=label, default=str(data.get(key, "")), required=False, max_length=60)
            self.boxes[key] = box
            self.add_item(box)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Nation")
        for key, box in self.boxes.items():
            cog.data[key] = box.value.strip()
        await cog.touch()
        await reply(interaction, "✅ Overview updated.")


class NationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for label, url in cfg.LINKS.items():
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))

    @staticmethod
    def _cog(i: discord.Interaction) -> "Nation":
        return i.client.get_cog("Nation")

    @discord.ui.button(label="Towns", style=discord.ButtonStyle.primary, custom_id="castro:nation:towns")
    async def towns(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).towns_embed())

    @discord.ui.button(label="Government", style=discord.ButtonStyle.primary, custom_id="castro:nation:gov")
    async def gov(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).gov_embed())

    @discord.ui.button(label="Relations", style=discord.ButtonStyle.primary, custom_id="castro:nation:rel")
    async def rel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).relations_embed())


class Nation(commands.Cog):
    nation = app_commands.Group(name="nation", description=f"{cfg.NATION_NAME} nation directory", guild_only=True)
    town = app_commands.Group(name="town", description="Manage the town list", parent=nation)
    gov = app_commands.Group(name="gov", description="Manage government positions", parent=nation)
    relation = app_commands.Group(name="relation", description="Manage diplomatic relations", parent=nation)

    def __init__(self, bot):
        self.bot = bot
        self.data = bot.store.data("nation", default_data())
        for key, value in default_data().items():
            self.data.setdefault(key, value)

    async def cog_load(self):
        self.bot.add_view(NationView())

    # ── embeds ────────────────────────────────────────────────────────────────
    def overview_embed(self) -> discord.Embed:
        d = self.data
        em = embed(f"{cfg.NATION_FLAG} {cfg.NATION_NAME} — Nation Directory", color=cfg.BLUE)
        em.add_field(name="Leader", value=d["leader"] or "—")
        em.add_field(name="Capital", value=d["capital"] or "—")
        em.add_field(name="Towns", value=str(len(d["towns"])))
        em.add_field(name="Residents", value=d["residents"] or "—")
        em.add_field(name="Bank", value=d["bank"] or "—")
        em.add_field(name="Claimed chunks", value=d["chunks"] or "—")
        em.add_field(name="Updated", value=stamp(d["updated"]), inline=False)
        em.set_footer(text="Maintained by leadership, not live game data. Use the buttons to browse.")
        return em

    def towns_embed(self) -> discord.Embed:
        towns = sorted(self.data["towns"], key=lambda x: x["name"].lower())
        lines = [f"**{t['name']}**" + (f" · mayor {t['mayor']}" if t.get("mayor") else "") +
                 (f" · {t['residents']} residents" if t.get("residents") else "") for t in towns]
        return embed("🏘️ Towns", "\n".join(lines) or "No towns listed yet.", cfg.BLUE)

    def gov_embed(self) -> discord.Embed:
        lines = [f"**{title}** — {person}" for title, person in self.data["government"].items()]
        return embed("🏛️ Government", "\n".join(lines) or "No positions listed yet.", cfg.RED)

    def relations_embed(self) -> discord.Embed:
        groups: dict[str, list[str]] = {}
        for nation, status in self.data["relations"].items():
            groups.setdefault(status, []).append(nation)
        em = embed("🌐 Diplomatic relations", color=cfg.GOLD)
        for status, label in RELATIONS.items():
            if status in groups:
                em.add_field(name=label, value="\n".join(sorted(groups[status])), inline=False)
        if not groups:
            em.description = "No relations listed yet."
        return em

    # ── panel ─────────────────────────────────────────────────────────────────
    async def post_panel(self, channel: discord.abc.Messageable) -> None:
        message = await channel.send(embed=self.overview_embed(), view=NationView())
        self.data["panel"] = {"channel": message.channel.id, "message": message.id}
        self.bot.store.save("nation")

    async def touch(self) -> None:
        """Record an edit and refresh the pinned directory message, if there is one."""
        self.data["updated"] = time.time()
        self.bot.store.save("nation")
        panel = self.data["panel"]
        if panel["channel"] and panel["message"]:
            try:
                channel = self.bot.get_channel(panel["channel"]) or await self.bot.fetch_channel(panel["channel"])
                await channel.get_partial_message(panel["message"]).edit(embed=self.overview_embed())
            except discord.HTTPException:
                pass

    # ── commands ──────────────────────────────────────────────────────────────
    @nation.command(name="view", description="Show the nation overview")
    async def view(self, interaction: discord.Interaction):
        await reply(interaction, embed=self.overview_embed())

    @nation.command(name="edit", description="Edit the overview (leadership)")
    @leadership_only()
    async def edit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditModal(self.data))

    @town.command(name="add", description="Add or update a town (leadership)")
    @app_commands.describe(name="Town name", mayor="Mayor's Minecraft name", residents="Number of residents")
    @leadership_only()
    async def town_add(self, interaction: discord.Interaction, name: str, mayor: str = "", residents: int | None = None):
        towns = [t for t in self.data["towns"] if t["name"].lower() != name.lower()]
        towns.append({"name": name, "mayor": mayor, "residents": residents})
        self.data["towns"] = towns
        await self.touch()
        await reply(interaction, f"✅ **{name}** saved. {len(towns)} towns listed.")

    @town.command(name="remove", description="Remove a town (leadership)")
    @leadership_only()
    async def town_remove(self, interaction: discord.Interaction, name: str):
        before = len(self.data["towns"])
        self.data["towns"] = [t for t in self.data["towns"] if t["name"].lower() != name.lower()]
        await self.touch()
        await reply(interaction, "✅ Removed." if len(self.data["towns"]) < before else "❌ No town with that name.")

    @gov.command(name="set", description="Set who holds a position (leadership)")
    @app_commands.describe(title="e.g. President", person="Who holds it")
    @leadership_only()
    async def gov_set(self, interaction: discord.Interaction, title: str, person: str):
        self.data["government"][title] = person
        await self.touch()
        await reply(interaction, f"✅ **{title}** → {person}")

    @gov.command(name="remove", description="Remove a position (leadership)")
    @leadership_only()
    async def gov_remove(self, interaction: discord.Interaction, title: str):
        removed = self.data["government"].pop(title, None)
        await self.touch()
        await reply(interaction, "✅ Removed." if removed else "❌ No position with that title.")

    @relation.command(name="set", description="Set relations with another nation (leadership)")
    @app_commands.describe(nation="Nation name", status="Current relationship")
    @app_commands.choices(status=[app_commands.Choice(name=v, value=k) for k, v in RELATIONS.items()])
    @leadership_only()
    async def rel_set(self, interaction: discord.Interaction, nation: str, status: app_commands.Choice[str]):
        self.data["relations"][nation] = status.value
        await self.touch()
        await reply(interaction, f"✅ **{nation}**: {status.name}")

    @relation.command(name="remove", description="Remove a nation from relations (leadership)")
    @leadership_only()
    async def rel_remove(self, interaction: discord.Interaction, nation: str):
        removed = self.data["relations"].pop(nation, None)
        await self.touch()
        await reply(interaction, "✅ Removed." if removed else "❌ That nation isn't listed.")


async def setup(bot):
    await bot.add_cog(Nation(bot))
