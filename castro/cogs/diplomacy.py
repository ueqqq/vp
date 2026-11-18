"""Treaty register: a clear public record of what the nation has agreed with whom."""

from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.ui import embed, leadership_only, reply, stamp

KINDS = {"alliance": "🤝 Alliance", "trade": "💱 Trade agreement", "non_aggression": "🕊️ Non-aggression pact",
         "peace": "☮️ Peace treaty", "other": "📄 Other"}
STATUSES = {"draft": "📝 Draft", "active": "✅ Active", "expired": "⌛ Expired", "terminated": "❌ Terminated"}
COLORS = {"draft": cfg.GREY, "active": cfg.GREEN, "expired": cfg.GREY, "terminated": cfg.RED}


class Diplomacy(commands.Cog):
    treaty = app_commands.Group(name="treaty", description="Treaty register", guild_only=True)

    def __init__(self, bot):
        self.bot = bot

    def _treaties(self) -> dict:
        return self.bot.store.data("treaties", {"next": 1, "items": {}})

    def build(self, t: dict) -> discord.Embed:
        em = embed(f"{KINDS[t['kind']]} with {t['partner']}", t["summary"], COLORS[t["status"]])
        em.add_field(name="Status", value=STATUSES[t["status"]])
        em.add_field(name="Registered", value=stamp(t["created"], "D"))
        em.add_field(name="Last updated", value=stamp(t["updated"], "D"))
        em.set_footer(text=f"Treaty #{t['id']}")
        return em

    @treaty.command(name="add", description="Register a treaty (leadership)")
    @app_commands.describe(partner="The other nation", kind="Type of agreement", summary="What was agreed",
                           status="Current status (default: active)")
    @app_commands.choices(kind=[app_commands.Choice(name=v, value=k) for k, v in KINDS.items()],
                          status=[app_commands.Choice(name=v, value=k) for k, v in STATUSES.items()])
    @leadership_only()
    async def add(self, interaction: discord.Interaction, partner: str, kind: app_commands.Choice[str],
                  summary: str, status: app_commands.Choice[str] | None = None):
        if len(summary) > 1500 or len(partner) > 80:
            return await reply(interaction, "❌ Partner must be 80 characters or fewer and summary 1500 or fewer.")
        store, now = self._treaties(), time.time()
        t = {"id": store["next"], "partner": partner.strip(), "kind": kind.value, "summary": summary.strip(),
             "status": status.value if status else "active", "created": now, "updated": now,
             "history": [[now, status.value if status else "active", interaction.user.id]], "channel": None, "message": None}
        channel = self.bot.settings.channel(interaction.guild, "treaties") or interaction.channel
        try:
            message = await channel.send(embed=self.build(t))
        except discord.HTTPException:
            return await reply(interaction, "❌ I couldn't post in that channel. Check my permissions.")
        t["channel"], t["message"] = channel.id, message.id
        store["items"][str(t["id"])] = t
        store["next"] += 1
        self.bot.store.save("treaties")
        await reply(interaction, f"✅ Treaty **#{t['id']}** registered in {channel.mention}.")

    @treaty.command(name="update", description="Change a treaty's status (leadership)")
    @app_commands.choices(status=[app_commands.Choice(name=v, value=k) for k, v in STATUSES.items()])
    @leadership_only()
    async def update(self, interaction: discord.Interaction, number: int, status: app_commands.Choice[str]):
        t = self._treaties()["items"].get(str(number))
        if not t:
            return await reply(interaction, "❌ No treaty with that number.")
        t["status"], t["updated"] = status.value, time.time()
        t["history"].append([t["updated"], status.value, interaction.user.id])
        self.bot.store.save("treaties")
        try:
            channel = interaction.guild.get_channel(t["channel"])
            await channel.get_partial_message(t["message"]).edit(embed=self.build(t))
        except (discord.HTTPException, AttributeError):
            pass
        await reply(interaction, f"✅ Treaty #{number} is now **{status.name}**.")

    @treaty.command(name="view", description="Show a treaty")
    async def view(self, interaction: discord.Interaction, number: int):
        t = self._treaties()["items"].get(str(number))
        await reply(interaction, embed=self.build(t)) if t else await reply(interaction, "❌ No treaty with that number.")

    @treaty.command(name="list", description="List treaties")
    @app_commands.choices(status=[app_commands.Choice(name=v, value=k) for k, v in STATUSES.items()])
    async def list(self, interaction: discord.Interaction, status: app_commands.Choice[str] | None = None):
        items = [t for t in self._treaties()["items"].values() if not status or t["status"] == status.value]
        items.sort(key=lambda t: t["id"], reverse=True)
        rows = [f"`#{t['id']}` {STATUSES[t['status']]} · {KINDS[t['kind']]} · **{t['partner']}**" for t in items[:20]]
        await reply(interaction, embed=embed("📚 Treaty register", "\n".join(rows) or "No treaties registered.", cfg.GOLD))


async def setup(bot):
    await bot.add_cog(Diplomacy(bot))
