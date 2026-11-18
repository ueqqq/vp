"""Nation directory — hand-maintained overview of Cuba on DiplomaticaMC."""

from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.ui import embed, ident, leadership_only, nation, reply, stamp, success


RELATIONS = {
    "ally": "🤝 Ally",
    "friendly": "🙂 Friendly",
    "neutral": "😐 Neutral",
    "hostile": "😠 Hostile",
    "at_war": "⚔️ At war",
}


def default_data() -> dict:
    return {
        "leader": "",
        "capital": "",
        "residents": "",
        "bank": "",
        "chunks": "",
        "updated": None,
        "towns": [],
        "government": {},
        "relations": {},
        "panel": {"channel": None, "message": None},
    }


class EditModal(discord.ui.Modal, title="Edit Nation Overview"):
    def __init__(self, data: dict):
        super().__init__()
        self.boxes = {}
        for key, label in (
            ("leader", "Leader"),
            ("capital", "Capital"),
            ("residents", "Residents"),
            ("bank", "Bank (e.g. 2g)"),
            ("chunks", "Claimed chunks"),
        ):
            box = discord.ui.TextInput(
                label=label,
                default=str(data.get(key, "") or ""),
                required=False,
                max_length=60,
            )
            self.boxes[key] = box
            self.add_item(box)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Nation")
        for key, box in self.boxes.items():
            cog.data[key] = box.value.strip()
        await cog.touch()
        await reply(interaction, embed=success("Overview updated", "The nation directory has been refreshed."))


class NationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for label, url in cfg.LINKS.items():
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))

    @staticmethod
    def _cog(i: discord.Interaction) -> "Nation":
        return i.client.get_cog("Nation")

    @discord.ui.button(label="Towns", emoji="🏘️", style=discord.ButtonStyle.primary, custom_id="castro:nation:towns")
    async def towns(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).towns_embed(interaction.guild_id))

    @discord.ui.button(label="Government", emoji="🏛️", style=discord.ButtonStyle.primary, custom_id="castro:nation:gov")
    async def gov(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).gov_embed(interaction.guild_id))

    @discord.ui.button(label="Relations", emoji="🌐", style=discord.ButtonStyle.primary, custom_id="castro:nation:rel")
    async def rel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await reply(interaction, embed=self._cog(interaction).relations_embed(interaction.guild_id))


class Nation(commands.Cog):
    nation = app_commands.Group(name="nation", description="Nation directory", guild_only=True)
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
    def overview_embed(self, guild_id: int | None = None) -> discord.Embed:
        d, i = self.data, ident(guild_id)
        em = nation(f"{i.name} — Nation Directory", guild_id=guild_id)
        if i.motto:
            em.description = f"*{i.motto}*"
        em.add_field(name="Leader", value=d["leader"] or "—", inline=True)
        em.add_field(name="Capital", value=d["capital"] or "—", inline=True)
        em.add_field(name="Towns", value=str(len(d["towns"])), inline=True)
        em.add_field(name="Residents", value=d["residents"] or "—", inline=True)
        em.add_field(name="Bank", value=d["bank"] or "—", inline=True)
        em.add_field(name="Claimed chunks", value=d["chunks"] or "—", inline=True)
        em.add_field(name="Last updated", value=stamp(d["updated"]), inline=False)
        em.set_footer(text="Maintained by leadership · not live game data · use the buttons below")
        return em

    def towns_embed(self, guild_id: int | None = None) -> discord.Embed:
        i = ident(guild_id)
        towns = sorted(self.data["towns"], key=lambda x: x["name"].lower())
        if not towns:
            return embed("🏘️ Towns", "No towns listed yet.\nLeadership can add them with `/nation town add`.", i.primary)
        lines = []
        for t in towns:
            line = f"**{t['name']}**"
            if t.get("mayor"):
                line += f" · mayor **{t['mayor']}**"
            if t.get("residents"):
                line += f" · {t['residents']} residents"
            lines.append(line)
        em = embed("🏘️ Towns", "\n".join(lines), i.primary)
        em.set_footer(text=f"{len(towns)} town{'s' if len(towns) != 1 else ''} · {i.name}")
        return em

    def gov_embed(self, guild_id: int | None = None) -> discord.Embed:
        i = ident(guild_id)
        if not self.data["government"]:
            return embed("🏛️ Government", "No positions listed yet.\nUse `/nation gov set` to add them.", i.accent)
        lines = [f"**{title}** — {person}" for title, person in sorted(self.data["government"].items())]
        em = embed("🏛️ Government", "\n".join(lines), i.accent)
        em.set_footer(text=f"{i.name} · Leadership")
        return em

    def relations_embed(self, guild_id: int | None = None) -> discord.Embed:
        i = ident(guild_id)
        groups: dict[str, list[str]] = {}
        for name, status in self.data["relations"].items():
            groups.setdefault(status, []).append(name)
        em = embed("🌐 Diplomatic Relations", color=cfg.GOLD)
        if not groups:
            em.description = "No relations recorded yet.\nUse `/nation relation set` to add them."
        else:
            for status, label in RELATIONS.items():
                if status in groups:
                    em.add_field(name=label, value="\n".join(f"• {n}" for n in sorted(groups[status])), inline=False)
        em.set_footer(text=f"{i.name} · Foreign Affairs")
        return em

    # ── panel ─────────────────────────────────────────────────────────────────
    async def post_panel(self, channel: discord.abc.Messageable) -> None:
        gid = getattr(getattr(channel, "guild", None), "id", None)
        message = await channel.send(embed=self.overview_embed(gid), view=NationView())
        self.data["panel"] = {"channel": message.channel.id, "message": message.id, "guild": gid}
        self.bot.store.save("nation")

    async def touch(self) -> None:
        self.data["updated"] = time.time()
        self.bot.store.save("nation")
        panel = self.data["panel"]
        if panel.get("channel") and panel.get("message"):
            try:
                channel = self.bot.get_channel(panel["channel"]) or await self.bot.fetch_channel(panel["channel"])
                await channel.get_partial_message(panel["message"]).edit(embed=self.overview_embed(panel.get("guild")))
            except discord.HTTPException:
                pass

    # ── commands ──────────────────────────────────────────────────────────────
    @nation.command(name="view", description="Show the full nation overview")
    async def view(self, interaction: discord.Interaction):
        await reply(interaction, embed=self.overview_embed(interaction.guild_id))

    @nation.command(name="edit", description="Edit the nation overview (leadership)")
    @leadership_only()
    async def edit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditModal(self.data))

    @town.command(name="add", description="Add or update a town (leadership)")
    @app_commands.describe(name="Town name", mayor="Mayor (optional)", residents="Resident count (optional)")
    @leadership_only()
    async def town_add(self, interaction: discord.Interaction, name: str, mayor: str | None = None, residents: str | None = None):
        towns = [t for t in self.data["towns"] if t["name"].lower() != name.lower()]
        towns.append({"name": name.strip(), "mayor": (mayor or "").strip() or None, "residents": (residents or "").strip() or None})
        self.data["towns"] = towns
        await self.touch()
        await reply(interaction, embed=success("Town saved", f"**{name}** is now listed. Total towns: **{len(towns)}**."))

    @town.command(name="remove", description="Remove a town (leadership)")
    @app_commands.describe(name="Exact town name")
    @leadership_only()
    async def town_remove(self, interaction: discord.Interaction, name: str):
        before = len(self.data["towns"])
        self.data["towns"] = [t for t in self.data["towns"] if t["name"].lower() != name.lower()]
        await self.touch()
        if len(self.data["towns"]) < before:
            await reply(interaction, embed=success("Town removed", f"**{name}** has been removed from the directory."))
        else:
            await reply(interaction, embed=embed("❌ Not found", f"No town named **{name}**.", cfg.RED))

    @gov.command(name="set", description="Set who holds a government position (leadership)")
    @app_commands.describe(title="Position title (e.g. President)", person="Who holds it")
    @leadership_only()
    async def gov_set(self, interaction: discord.Interaction, title: str, person: str):
        self.data["government"][title.strip()] = person.strip()
        await self.touch()
        await reply(interaction, embed=success("Position set", f"**{title}** → **{person}**"))

    @gov.command(name="remove", description="Remove a government position (leadership)")
    @app_commands.describe(title="Position title to remove")
    @leadership_only()
    async def gov_remove(self, interaction: discord.Interaction, title: str):
        removed = self.data["government"].pop(title.strip(), None)
        await self.touch()
        if removed:
            await reply(interaction, embed=success("Position removed", f"**{title}** has been cleared."))
        else:
            await reply(interaction, embed=embed("❌ Not found", f"No position titled **{title}**.", cfg.RED))

    @relation.command(name="set", description="Set diplomatic status with another nation (leadership)")
    @app_commands.describe(nation="Other nation name", status="Current relationship")
    @app_commands.choices(status=[app_commands.Choice(name=v, value=k) for k, v in RELATIONS.items()])
    @leadership_only()
    async def rel_set(self, interaction: discord.Interaction, nation: str, status: app_commands.Choice[str]):
        self.data["relations"][nation.strip()] = status.value
        await self.touch()
        await reply(interaction, embed=success("Relation updated", f"**{nation}** is now marked as **{status.name}**."))

    @relation.command(name="remove", description="Remove a nation from the relations list (leadership)")
    @app_commands.describe(nation="Nation name to remove")
    @leadership_only()
    async def rel_remove(self, interaction: discord.Interaction, nation: str):
        removed = self.data["relations"].pop(nation.strip(), None)
        await self.touch()
        if removed:
            await reply(interaction, embed=success("Relation removed", f"**{nation}** has been cleared."))
        else:
            await reply(interaction, embed=embed("❌ Not found", f"**{nation}** is not on the relations list.", cfg.RED))


async def setup(bot):
    await bot.add_cog(Nation(bot))
