"""Vote party: live tracker, 'I voted' claims, role pings, reminders, leaderboard."""

from __future__ import annotations

import asyncio
import logging
import re
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core import config as cfg
from core.i18n import t
from core.schema import render_template
from core.ui import admin_only, bar, embed, ident, reply, stamp
from votes.engine import (CELEBRATION, CLOSE, FINAL, MOMENTUM, NORMAL, WAITING, VoteEngine,
                          new_state, try_claim)
from votes.scraper import VoteScraper

log = logging.getLogger("castro.votes")

PHASES = {
    WAITING: (cfg.GREY, "⏳ Waiting for data"),
    NORMAL: (cfg.BLUE, "🗳️ Votes are coming in"),
    MOMENTUM: (cfg.GOLD, "🔥 Over halfway there"),
    CLOSE: (cfg.RED, "🚨 Vote party is close"),
    FINAL: (cfg.RED, "🏁 Final stretch"),
    CELEBRATION: (cfg.GREEN, "🎉 Vote party time"),
}
IGN_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


class VoteView(discord.ui.View):
    """Persistent buttons under the tracker. custom_ids must never change or old messages break."""

    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    def _cog(interaction: discord.Interaction) -> "Votes":
        return interaction.client.get_cog("Votes")

    @discord.ui.button(label="I voted", emoji="✅", style=discord.ButtonStyle.success, custom_id="castro:vote:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cog(interaction).handle_claim(interaction)

    @discord.ui.button(label="Get pinged", emoji="🔔", style=discord.ButtonStyle.primary, custom_id="castro:vote:notify")
    async def notify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cog(interaction).handle_notify(interaction)

    @discord.ui.button(label="How to vote", emoji="📖", style=discord.ButtonStyle.secondary, custom_id="castro:vote:howto")
    async def howto(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines = [f"{s['emoji']} [{s['name']}]({s['vote_url']})" for s in cfg.VOTE_SITES]
        em = embed("How to vote", "Vote once on each site (every site allows one vote per day), "
                   "then press **I voted** on the tracker.\n\n" + "\n".join(lines))
        await reply(interaction, embed=em)

    @discord.ui.button(label="Remind me", emoji="⏰", style=discord.ButtonStyle.secondary, custom_id="castro:vote:remind")
    async def remind(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cog(interaction).handle_remind(interaction)

    @discord.ui.button(label="Leaderboard", emoji="🏆", style=discord.ButtonStyle.secondary, custom_id="castro:vote:board")
    async def board(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cog(interaction).show_leaderboard(interaction)


class Votes(commands.Cog):
    voteparty = app_commands.Group(name="voteparty", description="Vote party tracker admin tools",
                                   guild_only=True, default_permissions=discord.Permissions(administrator=True))

    def __init__(self, bot):
        self.bot = bot
        state = bot.store.data("votes", new_state(cfg.VOTE_GOAL))
        self.engine = VoteEngine(state, [s["name"] for s in cfg.VOTE_SITES], cfg.VOTE_GOAL,
                                 cfg.PING_THRESHOLD, cfg.MAX_JUMP, cfg.STALE_AFTER)
        self.scraper = VoteScraper(cfg.VOTE_SITES)
        self.lock = asyncio.Lock()

    @property
    def guild_id(self) -> int:
        """The server this tracker belongs to (set by /voteparty setup)."""
        gid = self.engine.state["tracker"].get("guild")
        return gid or (self.bot.guilds[0].id if self.bot.guilds else 0)

    def opt(self, key: str):
        return self.bot.settings.get(self.guild_id, key)

    def _configure(self) -> None:
        self.engine.configure(self.opt("vote_goal"), self.opt("ping_threshold"))

    @commands.Cog.listener("on_castro_setting_changed")
    async def _on_setting(self, guild_id: int, key: str):
        if guild_id == self.guild_id and (key.startswith(("vote", "ping", "claim", "nation", "theme", "accent"))):
            self._configure()
            await self.update_tracker()

    async def cog_load(self):
        await self.scraper.start()
        self.bot.add_view(VoteView())
        self.poll.start()
        self.reminders.start()

    async def cog_unload(self):
        self.poll.cancel()
        self.reminders.cancel()
        await self.scraper.close()

    # ── background work ───────────────────────────────────────────────────────
    @tasks.loop(seconds=cfg.SCRAPE_INTERVAL)
    async def poll(self):
        try:
            await self.refresh()
        except Exception:
            log.exception("vote refresh failed; will retry next cycle")
        # Poll faster when a party is imminent, since that's when votes land quickly.
        phase = self.engine.phase(time.time())
        normal = self.opt("poll_interval")
        wanted = min(self.opt("fast_interval"), normal) if phase in (CLOSE, FINAL) else normal
        if self.poll.seconds != wanted:
            self.poll.change_interval(seconds=wanted)

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30)
    async def reminders(self):
        try:
            due = self.bot.store.data("reminders", {})
            now = time.time()
            for uid, when in list(due.items()):
                if when > now:
                    continue
                del due[uid]
                self.bot.store.save("reminders")
                try:
                    user = await self.bot.fetch_user(int(uid))
                    await user.send(f"⏰ {ident(self.guild_id).flag} Time to vote again! Head to the vote-party channel for the links.")
                except discord.HTTPException:
                    pass  # DMs closed; nothing more to do
        except Exception:
            log.exception("reminder loop error")

    @reminders.before_loop
    async def _before_reminders(self):
        await self.bot.wait_until_ready()

    async def refresh(self) -> None:
        if not self.bot.settings.enabled(self.guild_id, "votes"):
            return
        async with self.lock:
            self._configure()
            readings = await self.scraper.scrape_all()
            result = self.engine.apply(readings, time.time())
            for site, why in result.rejected.items():
                log.warning("%s reading rejected: %s", site, why)
            self.bot.store.save("votes")
            await self.update_tracker()
            if result.completed:
                await self.announce_party()
            if result.should_ping and await self.send_ping():
                self.engine.mark_pinged()
                self.bot.store.save("votes")

    # ── tracker message ───────────────────────────────────────────────────────
    def build_embed(self) -> discord.Embed:
        e, now = self.engine, time.time()
        phase = e.phase(now)
        color, headline = PHASES[phase]
        em = embed(f"{ident(self.guild_id).flag} Vote Party", color=color)
        if phase == WAITING:
            have = len(self.engine._sites_with_data())
            need = self.engine._majority()
            em.description = (f"{headline}\nWaiting for data from enough vote sites "
                              f"({have}/{need} needed to start).\n"
                              "Admins: `/voteparty status` shows what's failing.")
        else:
            lead = "🎉 **Vote party time!** Log in to collect.\n" if phase == CELEBRATION else ""
            em.description = (f"{lead}{headline}\n`{bar(e.progress, e.goal)}`\n"
                              f"**{e.progress}/{e.goal}** votes · **{e.remaining}** to go")
        stale = set(e.stale_sites(now))
        lines = []
        for site in cfg.VOTE_SITES:
            count = e.state["counts"].get(site["name"])
            shown = f"{count:,}" if count is not None else "—"
            warn = " ⚠️" if site["name"] in stale else ""
            lines.append(f"{site['emoji']} [{site['name']}]({site['vote_url']}) — {shown}{warn}")
        em.add_field(name="Vote here (all-time totals)", value="\n".join(lines), inline=False)
        if stale and phase != WAITING:
            em.add_field(name="⚠️ Heads up", value="Some sites haven't responded recently, so the count may be behind.", inline=False)
        em.add_field(name="Last checked", value=stamp(e.state["checked"]), inline=True)
        em.set_footer(text=f"Cycle #{e.state['cycle']} · up to {self.opt('claims_per_cycle')} claims per player per cycle")
        return em

    async def _tracker_channel(self):
        channel_id = self.engine.state["tracker"]["channel"]
        if not channel_id:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return None
        return channel

    async def update_tracker(self) -> None:
        channel = await self._tracker_channel()
        if channel is None:
            return
        tracker, em = self.engine.state["tracker"], self.build_embed()
        try:
            if tracker["message"]:
                await channel.get_partial_message(tracker["message"]).edit(embed=em)
                return
        except discord.NotFound:
            log.info("tracker message was deleted; posting a new one")
        except discord.HTTPException as exc:
            log.warning("could not edit tracker: %s", exc)
            return
        try:
            message = await channel.send(embed=em, view=VoteView())
        except discord.HTTPException as exc:
            log.warning("could not post tracker: %s", exc)
            return
        tracker["message"] = message.id
        self.bot.store.save("votes")

    async def send_ping(self) -> bool:
        channel = await self._tracker_channel()
        if channel is None or not getattr(channel, "guild", None):
            return False
        role = self.bot.settings.role(channel.guild, "vp")
        mention = role.mention if role else ""
        i = ident(channel.guild.id)
        text = render_template(self.opt("ping_message"), role=mention, remaining=self.engine.remaining,
                               nation=i.name, flag=i.flag).strip()
        try:
            await channel.send(text, delete_after=self.opt("ping_delete_minutes") * 60,
                               allowed_mentions=discord.AllowedMentions(roles=True))
            return True
        except discord.HTTPException as exc:
            log.warning("could not send ping: %s", exc)
            return False

    async def announce_party(self) -> None:
        channel = await self._tracker_channel()
        if channel:
            try:
                i = ident(self.guild_id)
                await channel.send(render_template(self.opt("celebration_message"), nation=i.name, flag=i.flag),
                                   delete_after=3600)
            except discord.HTTPException:
                pass

    # ── button handlers ───────────────────────────────────────────────────────
    async def handle_claim(self, interaction: discord.Interaction) -> None:
        lang = self.bot.lang(interaction.user.id, interaction.guild_id)
        players = self.bot.store.data("players", {})
        player = players.setdefault(str(interaction.user.id), {})
        ok, why, wait = try_claim(player, self.engine.state["cycle"], time.time(),
                                  self.opt("claims_per_cycle"), self.opt("claim_cooldown_min") * 60)
        if ok:
            text = t("claim_ok", lang, n=player["claims_cycle"], max=self.opt("claims_per_cycle"))
            if not player.get("ign"):
                text += "\n" + t("claim_no_ign", lang)
        elif why == "limit":
            text = t("claim_limit", lang, max=self.opt("claims_per_cycle"))
        else:
            text = t("claim_cooldown", lang, ts=int(time.time()) + wait)
        self.bot.store.save("players")
        await reply(interaction, text)

    async def handle_notify(self, interaction: discord.Interaction) -> None:
        lang = self.bot.lang(interaction.user.id, interaction.guild_id)
        role = self.bot.settings.role(interaction.guild, "vp")
        if role is None or not isinstance(interaction.user, discord.Member):
            return await reply(interaction, t("notify_missing", lang))
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Vote party pings off")
                await reply(interaction, t("notify_off", lang))
            else:
                await interaction.user.add_roles(role, reason="Vote party pings on")
                await reply(interaction, t("notify_on", lang))
        except discord.Forbidden:
            await reply(interaction, t("notify_denied", lang))

    async def handle_remind(self, interaction: discord.Interaction) -> None:
        self.bot.store.data("reminders", {})[str(interaction.user.id)] = time.time() + cfg.REMINDER_DELAY
        self.bot.store.save("reminders")
        await reply(interaction, t("remind_set", self.bot.lang(interaction.user.id, interaction.guild_id)))

    async def show_leaderboard(self, interaction: discord.Interaction) -> None:
        players = self.bot.store.data("players", {})
        ranked = sorted(((uid, p.get("claims_total", 0)) for uid, p in players.items() if p.get("claims_total")),
                        key=lambda x: x[1], reverse=True)[:10]
        medals = ["🥇", "🥈", "🥉"]
        if not ranked:
            body = "No votes claimed yet. Be the first!"
        else:
            rows = []
            for i, (uid, total) in enumerate(ranked):
                ign = players[uid].get("ign")
                rows.append(f"{medals[i] if i < 3 else f'`{i + 1}.`'} <@{uid}>{f' ({ign})' if ign else ''} — **{total}**")
            body = "\n".join(rows)
        em = embed("🏆 Vote leaderboard", body, cfg.GOLD)
        em.set_footer(text=t("leaderboard_note", self.bot.lang(interaction.user.id, interaction.guild_id)))
        await reply(interaction, embed=em, allowed_mentions=discord.AllowedMentions.none())

    # ── user commands ─────────────────────────────────────────────────────────
    @app_commands.command(name="link", description="Link your Minecraft username")
    @app_commands.describe(ign="Your Minecraft username")
    async def link(self, interaction: discord.Interaction, ign: str):
        lang = self.bot.lang(interaction.user.id, interaction.guild_id)
        if not IGN_RE.match(ign):
            return await reply(interaction, t("link_bad", lang))
        self.bot.store.data("players", {}).setdefault(str(interaction.user.id), {})["ign"] = ign
        self.bot.store.save("players")
        await reply(interaction, t("link_ok", lang, ign=ign))

    @app_commands.command(name="myvotes", description="See your vote-party stats")
    async def myvotes(self, interaction: discord.Interaction):
        p = self.bot.store.data("players", {}).get(str(interaction.user.id), {})
        in_cycle = p.get("claims_cycle", 0) if p.get("cycle") == self.engine.state["cycle"] else 0
        em = embed("📊 Your votes", color=cfg.BLUE)
        em.add_field(name="Minecraft name", value=p.get("ign") or "not linked (`/link`)")
        em.add_field(name="This cycle", value=f"{in_cycle}/{self.opt('claims_per_cycle')}")
        em.add_field(name="All time", value=str(p.get("claims_total", 0)))
        if p.get("last_claim"):
            em.add_field(name="Last claim", value=stamp(p["last_claim"]))
        await reply(interaction, embed=em)

    @app_commands.command(name="leaderboard", description="Top vote claimers")
    async def leaderboard(self, interaction: discord.Interaction):
        await self.show_leaderboard(interaction)

    # ── admin commands ────────────────────────────────────────────────────────
    @voteparty.command(name="setup", description="Post the tracker in this channel")
    @admin_only()
    async def vp_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tracker = self.engine.state["tracker"]
        tracker["channel"], tracker["message"], tracker["guild"] = interaction.channel_id, None, interaction.guild_id
        self.bot.settings.set_channel(interaction.guild_id, "votes", interaction.channel_id)
        self.bot.store.save("votes")
        await self.refresh()
        await interaction.followup.send("✅ Tracker posted. It updates itself; no need to run this again.", ephemeral=True)

    @voteparty.command(name="forceupdate", description="Re-scrape the sites right now")
    @admin_only()
    async def vp_force(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.refresh()
        await interaction.followup.send("✅ Refreshed.", ephemeral=True)

    @voteparty.command(name="setremaining", description="Set how many votes remain in this cycle")
    @app_commands.describe(votes="Votes still needed (0 to the goal)")
    @admin_only()
    async def vp_remaining(self, interaction: discord.Interaction, votes: app_commands.Range[int, 0, 10000]):
        if not self.engine.set_remaining(votes, time.time()):
            return await reply(interaction, "❌ Can't do that yet: not enough sites have been read. Try `/voteparty forceupdate`.")
        self.bot.store.save("votes")
        await self.update_tracker()
        await reply(interaction, f"✅ Tracker now shows **{self.engine.remaining}** votes remaining.")

    @voteparty.command(name="rebase", description="Start a fresh cycle from the current vote totals")
    @admin_only()
    async def vp_rebase(self, interaction: discord.Interaction):
        if not self.engine.rebase(time.time()):
            return await reply(interaction, "❌ Not enough sites have been read yet. Try `/voteparty forceupdate`.")
        self.bot.store.save("votes")
        await self.update_tracker()
        await reply(interaction, "✅ New cycle started from the current totals.")

    @voteparty.command(name="status", description="Show scraper health for each vote site")
    @admin_only()
    async def vp_status(self, interaction: discord.Interaction):
        now = time.time()
        em = embed("🩺 Vote scraper health", color=cfg.BLUE)
        have = len(self.engine._sites_with_data())
        need = self.engine._majority()
        if not self.engine.ready:
            em.description = f"Tracker is **waiting** ({have}/{need} sites with data). It will start automatically once enough sites respond."
        for site in cfg.VOTE_SITES:
            h = self.scraper.health[site["name"]]
            total = h.ok + h.fail
            rate = f"{h.ok / total:.0%}" if total else "n/a"
            has_data = site["name"] in self.engine.state["counts"]
            status = "✅ has data" if has_data else "⏳ no data yet"
            lines = [f"{status} · Success rate: **{rate}** ({h.ok}/{total})", f"Last good read: {stamp(h.last_ok)}"]
            if h.consecutive_fail:
                lines.append(f"⚠️ {h.consecutive_fail} failures in a row: `{h.last_error}`")
            em.add_field(name=f"{site['emoji']} {site['name']}", value="\n".join(lines), inline=False)
        em.set_footer(text=f"Polling every {self.poll.seconds:.0f}s ({self.opt('poll_interval')}s normally, {self.opt('fast_interval')}s when close) · stale after {cfg.STALE_AFTER // 60} min")
        await reply(interaction, embed=em)


async def setup(bot):
    await bot.add_cog(Votes(bot))
