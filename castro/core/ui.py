"""Shared UI helpers — consistent Cuba-themed embeds, replies, and permission checks."""

from __future__ import annotations

import discord
from discord import app_commands

from core import config as cfg


def embed(
    title: str | None = None,
    description: str | None = None,
    color: int = cfg.BLUE,
) -> discord.Embed:
    """Base embed with optional Cuba footer branding."""
    em = discord.Embed(title=title, description=description, color=color)
    return em


def success(title: str, description: str | None = None) -> discord.Embed:
    em = embed(f"✅ {title}", description, cfg.GREEN)
    return em


def error(title: str, description: str | None = None) -> discord.Embed:
    em = embed(f"❌ {title}", description, cfg.RED)
    return em


def info(title: str, description: str | None = None) -> discord.Embed:
    return embed(title, description, cfg.BLUE)


def nation(title: str, description: str | None = None) -> discord.Embed:
    """Standard nation-branded embed (Cuba red accent)."""
    em = embed(f"{cfg.NATION_FLAG} {title}", description, cfg.RED)
    em.set_footer(text=f"{cfg.NATION_NAME} · Castro v{cfg.VERSION}")
    return em


def stamp(ts: float | None, style: str = "R") -> str:
    """Discord relative timestamp ('5 minutes ago')."""
    return f"<t:{int(ts)}:{style}>" if ts else "never"


def bar(done: int, total: int, width: int = 18) -> str:
    total = max(total, 1)
    filled = round(width * min(max(done, 0), total) / total)
    return "█" * filled + "░" * (width - filled)


async def reply(interaction: discord.Interaction, *args, **kwargs) -> None:
    """Respond or follow up, whichever is still allowed. Defaults to ephemeral."""
    kwargs.setdefault("ephemeral", True)
    if interaction.response.is_done():
        await interaction.followup.send(*args, **kwargs)
    else:
        await interaction.response.send_message(*args, **kwargs)


async def reply_ok(interaction: discord.Interaction, message: str) -> None:
    await reply(interaction, embed=success("Done", message))


async def reply_err(interaction: discord.Interaction, message: str) -> None:
    await reply(interaction, embed=error("Error", message))


# ── permission decorators ─────────────────────────────────────────────────────

def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.client.settings.is_admin(interaction.user):
            await reply(interaction, embed=error("Permission denied", "Administrators only."))
            return False
        return True
    return app_commands.check(predicate)


def leadership_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.client.settings.is_leadership(interaction.user):
            await reply(interaction, embed=error("Permission denied", "Leadership or administrators only."))
            return False
        return True
    return app_commands.check(predicate)


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.client.settings.is_staff(interaction.user):
            await reply(interaction, embed=error("Permission denied", "Staff, leadership or administrators only."))
            return False
        return True
    return app_commands.check(predicate)
