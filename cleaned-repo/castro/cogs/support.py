"""Nation Support panel: private ticket channels plus a shortcut to apply for government."""

from __future__ import annotations

import asyncio
import logging
import re
import time

import discord
from discord.ext import commands

from core import config as cfg
from core.ui import embed, reply, stamp

log = logging.getLogger("castro.support")


class TicketModal(discord.ui.Modal, title="Nation support"):
    subject = discord.ui.TextInput(label="What do you need help with?", max_length=100)
    details = discord.ui.TextInput(label="Details", style=discord.TextStyle.paragraph, required=False, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.get_cog("Support").open_ticket(interaction, self.subject.value, self.details.value)


class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Nation Support", style=discord.ButtonStyle.primary, custom_id="castro:support:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

    @discord.ui.button(label="Apply for government", style=discord.ButtonStyle.secondary, custom_id="castro:support:gov")
    async def gov(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.applications import ApplicationModal
        await interaction.response.send_modal(ApplicationModal("government"))


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="castro:ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.client.get_cog("Support").close_ticket(interaction)


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(SupportView())
        self.bot.add_view(TicketCloseView())

    def panel_embed(self) -> discord.Embed:
        return embed(f"{cfg.NATION_FLAG} Nation Support",
                     "Need help from leadership or staff? Open a **private ticket** and we'll get back to you.\n\n"
                     "Want to serve the nation? **Apply for government.** Applications are reviewed privately, "
                     "and being accepted doesn't automatically grant a role.", cfg.BLUE)

    async def post_panel(self, channel: discord.abc.Messageable) -> None:
        await channel.send(embed=self.panel_embed(), view=SupportView())

    def _tickets(self) -> dict:
        return self.bot.store.data("tickets", {"next": 1, "items": {}})

    async def open_ticket(self, interaction: discord.Interaction, subject: str, details: str) -> None:
        guild, user = interaction.guild, interaction.user
        tickets = self._tickets()
        for tk in tickets["items"].values():
            if tk["user"] == user.id and tk["status"] == "open":
                if guild.get_channel(tk["channel"]):
                    return await reply(interaction, f"You already have an open ticket: <#{tk['channel']}>")
                tk["status"] = "closed"  # channel vanished (deleted by hand); don't block them forever

        s = self.bot.settings
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True,
                                                  embed_links=True, read_message_history=True),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True,
                                              read_message_history=True),
        }
        for kind in ("staff", "leadership"):
            role = s.role(guild, kind)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                               attach_files=True, read_message_history=True)
        ticket_id = tickets["next"]
        category = s.channel(guild, "ticket_category")
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{ticket_id:04d}", overwrites=overwrites,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                topic=f"Ticket #{ticket_id} · opened by {user} ({user.id})", reason=f"Ticket by {user}")
        except discord.Forbidden:
            return await reply(interaction, "❌ I need the **Manage Channels** permission to create tickets.")

        tickets["next"] += 1
        tickets["items"][str(ticket_id)] = {"id": ticket_id, "user": user.id, "channel": channel.id, "subject": subject,
                                            "status": "open", "created": time.time()}
        self.bot.store.save("tickets")

        em = embed(f"🎫 Ticket #{ticket_id}: {subject}", details or "No extra details provided.", cfg.BLUE)
        em.add_field(name="Opened by", value=user.mention)
        em.add_field(name="Opened", value=stamp(time.time()))
        pings = " ".join(r.mention for r in (s.role(guild, "staff"), s.role(guild, "leadership")) if r)
        await channel.send(f"{user.mention} {pings}".strip(), embed=em, view=TicketCloseView(),
                           allowed_mentions=discord.AllowedMentions(users=True, roles=True))
        await reply(interaction, f"✅ Ticket opened: {channel.mention}")

    async def close_ticket(self, interaction: discord.Interaction) -> None:
        ticket = next((x for x in self._tickets()["items"].values()
                       if x["channel"] == interaction.channel_id and x["status"] == "open"), None)
        if ticket is None:
            return await reply(interaction, "This isn't an open ticket.")
        if not (self.bot.settings.is_staff(interaction.user) or interaction.user.id == ticket["user"]):
            return await reply(interaction, "❌ Only staff or the person who opened the ticket can close it.")
        ticket.update(status="closed", closed_by=interaction.user.id, closed_at=time.time())
        self.bot.store.save("tickets")
        await interaction.response.send_message("🔒 Closing this ticket in 5 seconds…")

        log_channel = self.bot.settings.channel(interaction.guild, "logs")
        if log_channel:
            em = embed(f"🎫 Ticket #{ticket['id']} closed", f"**Subject:** {ticket['subject']}", cfg.GREY)
            em.add_field(name="Opened by", value=f"<@{ticket['user']}>")
            em.add_field(name="Closed by", value=interaction.user.mention)
            em.add_field(name="Open for", value=f"{int((time.time() - ticket['created']) // 60)} min")
            try:
                await log_channel.send(embed=em, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket #{ticket['id']} closed by {interaction.user}")
        except discord.HTTPException:
            log.warning("could not delete ticket channel %s", interaction.channel_id)


async def setup(bot):
    await bot.add_cog(Support(bot))
