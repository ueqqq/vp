"""Citizenship / ally / government applications reviewed by leadership.

Applications are stored by id, and the review buttons look the application up from the message
they sit on, so they keep working across restarts.
"""

from __future__ import annotations

import logging
import re
import time

import discord
from discord.ext import commands

from core import config as cfg
from core.ui import embed, reply, stamp

log = logging.getLogger("castro.applications")

S, P = discord.TextStyle.short, discord.TextStyle.paragraph
IGN = ("Minecraft username", "Your in-game name", S, 16)
KINDS = {
    "citizenship": {
        "title": "🏠 Citizenship application", "color": cfg.BLUE, "role": "citizen",
        "fields": [IGN, ("Current nation and town", "e.g. Cuba, Havana", S, 100),
                   ("Why do you want to join?", "", P, 800)],
    },
    "ally": {
        "title": "🤝 Ally request", "color": cfg.GOLD, "role": "ally",
        "fields": [IGN, ("Your nation", "", S, 100), ("Your role in that nation", "e.g. Mayor, Diplomat", S, 100),
                   ("What are you proposing?", "", P, 800)],
    },
    "government": {
        "title": "🏛️ Government application", "color": cfg.RED, "role": None,  # never auto-grants a role
        "fields": [IGN, ("Position you're applying for", "", S, 100), ("Experience and what you'd bring", "", P, 800)],
    },
}


class ApplicationModal(discord.ui.Modal):
    def __init__(self, kind: str):
        super().__init__(title=KINDS[kind]["title"][:45])
        self.kind = kind
        self.inputs: list[tuple[str, discord.ui.TextInput]] = []
        for label, placeholder, style, limit in KINDS[kind]["fields"]:
            box = discord.ui.TextInput(label=label, placeholder=placeholder or None, style=style,
                                       max_length=limit, required=True)
            self.inputs.append((label, box))
            self.add_item(box)

    async def on_submit(self, interaction: discord.Interaction):
        answers = [(label, box.value.strip()) for label, box in self.inputs]
        await interaction.client.get_cog("Applications").submit(interaction, self.kind, answers)


class DenyModal(discord.ui.Modal, title="Deny application"):
    reason = discord.ui.TextInput(label="Reason (sent to the applicant)", style=P, required=False, max_length=500)

    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.get_cog("Applications").finish(interaction, self.app_id, False, self.reason.value.strip())


class ReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.success, custom_id="castro:app:approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Applications")
        app_id = await cog.check_reviewer(interaction)
        if app_id:
            await interaction.response.defer(ephemeral=True)
            await cog.finish(interaction, app_id, True, "")

    @discord.ui.button(label="Deny", emoji="❌", style=discord.ButtonStyle.danger, custom_id="castro:app:deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Applications")
        app_id = await cog.check_reviewer(interaction)
        if app_id:
            await interaction.response.send_modal(DenyModal(app_id))


class Applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ReviewView())

    def _apps(self) -> dict:
        return self.bot.store.data("applications", {"next": 1, "items": {}})

    def _embed(self, app: dict) -> discord.Embed:
        info = KINDS[app["kind"]]
        color = {"approved": cfg.GREEN, "denied": cfg.RED}.get(app["status"], info["color"])
        em = embed(f"{info['title']} · #{app['id']}", color=color)
        em.add_field(name="Applicant", value=f"<@{app['user']}>", inline=True)
        em.add_field(name="Submitted", value=stamp(app["created"]), inline=True)
        for label, value in app["answers"]:
            em.add_field(name=label, value=value[:1024] or "—", inline=False)
        if app["status"] != "pending":
            verdict = "✅ Approved" if app["status"] == "approved" else "❌ Denied"
            text = f"{verdict} by <@{app['reviewer']}>"
            if app.get("reason"):
                text += f"\n{app['reason']}"
            em.add_field(name="Decision", value=text, inline=False)
        return em

    async def submit(self, interaction: discord.Interaction, kind: str, answers: list) -> None:
        guild = interaction.guild
        channel = self.bot.settings.channel(guild, "applications") if guild else None
        if channel is None:
            return await reply(interaction, "❌ Leadership hasn't chosen where applications go yet. "
                                            "Ask an admin to run `/castro setchannel`.")
        apps = self._apps()
        for app in apps["items"].values():
            if app["user"] == interaction.user.id and app["kind"] == kind and app["status"] == "pending":
                return await reply(interaction, f"⏳ You already have a pending application (#{app['id']}). Hang tight!")
        app_id = str(apps["next"])
        app = {"id": app_id, "kind": kind, "user": interaction.user.id, "answers": answers,
               "status": "pending", "created": time.time(), "channel": channel.id, "message": None}
        try:
            message = await channel.send(embed=self._embed(app), view=ReviewView(),
                                         allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            return await reply(interaction, "❌ I couldn't post to the review channel. Tell an admin to check my permissions.")
        app["message"] = message.id
        apps["next"] += 1
        apps["items"][app_id] = app
        self.bot.store.save("applications")
        await reply(interaction, f"✅ Application **#{app_id}** sent to leadership. You'll get a DM when it's reviewed.")

    async def check_reviewer(self, interaction: discord.Interaction) -> str | None:
        """Permission + lookup shared by both buttons. Returns the application id, or None after replying."""
        if not self.bot.settings.is_leadership(interaction.user):
            await reply(interaction, "❌ Only leadership can review applications.")
            return None
        for app in self._apps()["items"].values():
            if app["message"] == interaction.message.id:
                if app["status"] != "pending":
                    await reply(interaction, f"This application was already {app['status']}.")
                    return None
                return app["id"]
        await reply(interaction, "❌ I can't find this application in my records.")
        return None

    async def finish(self, interaction: discord.Interaction, app_id: str, approved: bool, reason: str) -> None:
        app = self._apps()["items"].get(app_id)
        if not app or app["status"] != "pending":
            return await reply(interaction, "This application was already handled.")
        guild, notes = interaction.guild, []
        app.update(status="approved" if approved else "denied", reviewer=interaction.user.id,
                   reason=reason, reviewed=time.time())
        self.bot.store.save("applications")

        member = guild.get_member(app["user"])
        if approved and member:
            role_kind = KINDS[app["kind"]]["role"]
            if role_kind:
                role = self.bot.settings.role(guild, role_kind)
                if role is None:
                    notes.append(f"⚠️ No **{role_kind}** role is configured, so none was assigned (`/castro setrole`).")
                else:
                    try:
                        await member.add_roles(role, reason=f"Application #{app_id} approved by {interaction.user}")
                    except discord.Forbidden:
                        notes.append(f"⚠️ I couldn't give {role.mention}; my role must sit above it.")
            if app["kind"] == "citizenship":  # record the date, and link their IGN if they haven't yet
                record = self.bot.store.data("players", {}).setdefault(str(app["user"]), {})
                record.setdefault("citizen_since", time.time())
                ign = app["answers"][0][1]
                if re.fullmatch(r"[A-Za-z0-9_]{3,16}", ign):
                    record.setdefault("ign", ign)
                self.bot.store.save("players")

        title = KINDS[app["kind"]]["title"]
        if approved:
            text = ("Welcome aboard! Your role has been assigned." if KINDS[app["kind"]]["role"]
                    else "Leadership will contact you about next steps. (Approval doesn't automatically grant a role.)")
        else:
            text = "Unfortunately it wasn't approved this time." + (f"\n\n**Reason:** {reason}" if reason else "")
        try:
            user = member or await self.bot.fetch_user(app["user"])
            await user.send(embed=embed(f"{title} · {'approved ✅' if approved else 'denied ❌'}", text,
                                        cfg.GREEN if approved else cfg.RED))
        except discord.HTTPException:
            notes.append("⚠️ I couldn't DM the applicant (their DMs are closed).")

        try:
            channel = guild.get_channel(app["channel"])
            await channel.get_partial_message(app["message"]).edit(embed=self._embed(app), view=None)
        except (discord.HTTPException, AttributeError):
            notes.append("⚠️ I couldn't update the review message.")
        await reply(interaction, f"{'✅ Approved' if approved else '❌ Denied'} application #{app_id}.\n" + "\n".join(notes))


async def setup(bot):
    await bot.add_cog(Applications(bot))
