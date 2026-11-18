"""Government: numbered decrees and citizen polls."""

from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core import config as cfg
from core import polls
from core.ui import bar, embed, leadership_only, reply, stamp

log = logging.getLogger("castro.government")


# ── decrees ───────────────────────────────────────────────────────────────────
class DecreeModal(discord.ui.Modal, title="Publish a decree"):
    heading = discord.ui.TextInput(label="Title", max_length=100)
    text = discord.ui.TextInput(label="Text", style=discord.TextStyle.paragraph, max_length=1800)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.get_cog("Government").publish_decree(interaction, self.heading.value.strip(), self.text.value.strip())


# ── polls ─────────────────────────────────────────────────────────────────────
class PollModal(discord.ui.Modal, title="Create a poll"):
    question = discord.ui.TextInput(label="Question", max_length=200)
    options = discord.ui.TextInput(label="Options (one per line, 2 to 4)", style=discord.TextStyle.paragraph, max_length=400)
    hours = discord.ui.TextInput(label="Open for how many hours? (1 to 168)", default="24", max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.get_cog("Government").create_poll(
            interaction, self.question.value.strip(), self.options.value, self.hours.value.strip())


class PollView(discord.ui.View):
    """One persistent button per option. The poll is found from the message the button sits on."""

    def __init__(self, options: list[str] | None = None):
        super().__init__(timeout=None)
        for i in range(len(options) if options else 4):
            label = f"{i + 1}. {options[i]}"[:80] if options else f"Option {i + 1}"
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"castro:poll:{i}")
            button.callback = self._callback(i)
            self.add_item(button)

    @staticmethod
    def _callback(index: int):
        async def callback(interaction: discord.Interaction):
            await interaction.client.get_cog("Government").vote(interaction, index)
        return callback


class Government(commands.Cog):
    decree = app_commands.Group(name="decree", description="Government decrees", guild_only=True)
    poll = app_commands.Group(name="poll", description="Citizen polls", guild_only=True)

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(PollView())
        self.expire_polls.start()

    async def cog_unload(self):
        self.expire_polls.cancel()

    def _decrees(self) -> dict:
        return self.bot.store.data("decrees", {"next": 1, "items": {}})

    def _polls(self) -> dict:
        return self.bot.store.data("polls", {"next": 1, "items": {}})

    # ── decrees ───────────────────────────────────────────────────────────────
    def decree_embed(self, d: dict) -> discord.Embed:
        repealed = d["status"] == "repealed"
        em = embed(f"📜 Decree #{d['id']}: {d['title']}", d["text"], cfg.GREY if repealed else cfg.RED)
        em.add_field(name="Issued by", value=f"<@{d['author']}>")
        em.add_field(name="Date", value=stamp(d["created"], "D"))
        if repealed:
            em.add_field(name="Status", value=f"❌ Repealed {stamp(d['repealed_at'], 'D')}", inline=False)
        return em

    async def publish_decree(self, interaction: discord.Interaction, title: str, text: str) -> None:
        channel = self.bot.settings.channel(interaction.guild, "decrees") or interaction.channel
        decrees = self._decrees()
        d = {"id": decrees["next"], "title": title, "text": text, "author": interaction.user.id,
             "created": time.time(), "status": "active", "channel": channel.id, "message": None}
        try:
            message = await channel.send(embed=self.decree_embed(d), allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            return await reply(interaction, "❌ I couldn't post in that channel. Check my permissions.")
        d["message"] = message.id
        decrees["items"][str(d["id"])] = d
        decrees["next"] += 1
        self.bot.store.save("decrees")
        await reply(interaction, f"✅ Decree **#{d['id']}** published in {channel.mention}.")

    @decree.command(name="publish", description="Publish a new decree (leadership)")
    @leadership_only()
    async def decree_publish(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DecreeModal())

    @decree.command(name="repeal", description="Repeal a decree (leadership)")
    @leadership_only()
    async def decree_repeal(self, interaction: discord.Interaction, number: int):
        d = self._decrees()["items"].get(str(number))
        if not d:
            return await reply(interaction, "❌ No decree with that number.")
        if d["status"] == "repealed":
            return await reply(interaction, "That decree is already repealed.")
        d.update(status="repealed", repealed_at=time.time(), repealed_by=interaction.user.id)
        self.bot.store.save("decrees")
        try:
            channel = interaction.guild.get_channel(d["channel"])
            await channel.get_partial_message(d["message"]).edit(embed=self.decree_embed(d))
        except (discord.HTTPException, AttributeError):
            pass
        await reply(interaction, f"✅ Decree #{number} repealed.")

    @decree.command(name="view", description="Read a decree")
    async def decree_view(self, interaction: discord.Interaction, number: int):
        d = self._decrees()["items"].get(str(number))
        await reply(interaction, embed=self.decree_embed(d)) if d else await reply(interaction, "❌ No decree with that number.")

    @decree.command(name="list", description="List recent decrees")
    async def decree_list(self, interaction: discord.Interaction):
        items = sorted(self._decrees()["items"].values(), key=lambda d: d["id"], reverse=True)[:15]
        rows = []
        for d in items:
            link = f"https://discord.com/channels/{interaction.guild_id}/{d['channel']}/{d['message']}"
            mark = "~~" if d["status"] == "repealed" else ""
            rows.append(f"`#{d['id']}` {mark}[{d['title']}]({link}){mark}")
        await reply(interaction, embed=embed("📜 Decrees", "\n".join(rows) or "No decrees yet.", cfg.RED))

    # ── polls ─────────────────────────────────────────────────────────────────
    def poll_embed(self, p: dict) -> discord.Embed:
        counts, total = polls.tally(p), sum(polls.tally(p))
        top = set(polls.winners(p)) if p["status"] != "open" else set()
        blocks = []
        for i, (option, n) in enumerate(zip(p["options"], counts)):
            crown = " 🏆" if i in top and len(top) == 1 else ""
            blocks.append(f"**{i + 1}. {option}**{crown}\n`{bar(n, max(total, 1), 14)}` {n} ({(n / total if total else 0):.0%})")
        em = embed(f"📊 {p['question']}", "\n\n".join(blocks), cfg.GOLD if p["status"] == "open" else cfg.GREY)
        if p["status"] == "open":
            em.add_field(name="Closes", value=stamp(p["closes"]))
        else:
            result = "Tie" if len(top) > 1 else ("No votes" if not top else "Closed")
            em.add_field(name="Status", value=f"🔒 {result}")
        em.add_field(name="Votes cast", value=str(total))
        em.set_footer(text=f"Poll #{p['id']} · one vote each, changeable until close · votes are recorded by member, not secret")
        return em

    async def create_poll(self, interaction: discord.Interaction, question: str, raw: str, hours_text: str) -> None:
        options, error = polls.parse_options(raw)
        if error:
            return await reply(interaction, f"❌ {error}")
        if not hours_text.isdigit() or not 1 <= int(hours_text) <= 168:
            return await reply(interaction, "❌ Duration must be a whole number of hours from 1 to 168.")
        store, now = self._polls(), time.time()
        p = polls.new_poll(str(store["next"]), question, options, interaction.user.id, now, now + int(hours_text) * 3600)
        try:
            message = await interaction.channel.send(embed=self.poll_embed(p), view=PollView(options))
        except discord.HTTPException:
            return await reply(interaction, "❌ I couldn't post in this channel. Check my permissions.")
        p["channel"], p["message"] = interaction.channel_id, message.id
        store["items"][p["id"]] = p
        store["next"] += 1
        self.bot.store.save("polls")
        await reply(interaction, f"✅ Poll **#{p['id']}** is live.")

    def _poll_for(self, message_id: int) -> dict | None:
        return next((p for p in self._polls()["items"].values() if p["message"] == message_id), None)

    async def vote(self, interaction: discord.Interaction, index: int) -> None:
        p = self._poll_for(interaction.message.id)
        if p is None:
            return await reply(interaction, "❌ I can't find this poll in my records.")
        s, user = self.bot.settings, interaction.user
        if (s.get(interaction.guild_id, "poll_citizens_only") and s.role(interaction.guild, "citizen")
                and not (s.has_role(user, "citizen") or s.is_staff(user))):
            return await reply(interaction, "❌ Only citizens can vote in nation polls.")
        result = polls.cast(p, user.id, index)
        if result == "closed":
            return await reply(interaction, "🔒 This poll has closed.")
        if result == "invalid":
            return await reply(interaction, "❌ That option doesn't exist.")
        self.bot.store.save("polls")
        await interaction.response.edit_message(embed=self.poll_embed(p))
        note = {"ok": "✅ Vote recorded.", "changed": "🔄 Vote changed.", "same": "You already picked that option."}[result]
        await interaction.followup.send(f"{note} **{p['options'][index]}**", ephemeral=True)

    async def close_poll(self, p: dict) -> None:
        polls.close(p, time.time())
        self.bot.store.save("polls")
        try:
            channel = self.bot.get_channel(p["channel"]) or await self.bot.fetch_channel(p["channel"])
            await channel.get_partial_message(p["message"]).edit(embed=self.poll_embed(p), view=None)
        except discord.HTTPException:
            log.warning("could not update closed poll #%s", p["id"])

    @tasks.loop(seconds=30)
    async def expire_polls(self):
        try:
            now = time.time()
            for p in list(self._polls()["items"].values()):
                if polls.is_expired(p, now):
                    await self.close_poll(p)
        except Exception:
            log.exception("poll expiry check failed")

    @expire_polls.before_loop
    async def _before_expire(self):
        await self.bot.wait_until_ready()

    @poll.command(name="create", description="Start a citizen poll in this channel (leadership)")
    @leadership_only()
    async def poll_create(self, interaction: discord.Interaction):
        modal = PollModal()
        modal.hours.default = str(self.bot.settings.get(interaction.guild_id, "poll_default_hours"))
        await interaction.response.send_modal(modal)

    @poll.command(name="close", description="Close a poll early (leadership)")
    @leadership_only()
    async def poll_close(self, interaction: discord.Interaction, number: int):
        p = self._polls()["items"].get(str(number))
        if not p or p["status"] != "open":
            return await reply(interaction, "❌ No open poll with that number.")
        await self.close_poll(p)
        await reply(interaction, f"✅ Poll #{number} closed.")

    @poll.command(name="results", description="See a poll's current results")
    async def poll_results(self, interaction: discord.Interaction, number: int):
        p = self._polls()["items"].get(str(number))
        await reply(interaction, embed=self.poll_embed(p)) if p else await reply(interaction, "❌ No poll with that number.")


async def setup(bot):
    await bot.add_cog(Government(bot))
