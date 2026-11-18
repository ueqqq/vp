"""Small shared helpers for building embeds."""

from __future__ import annotations

import discord

from core import config as cfg


def embed(title: str | None = None, description: str | None = None, color: int = cfg.BLUE) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def stamp(ts: float | None, style: str = "R") -> str:
    """Discord timestamp that renders in each viewer's own timezone ('5 minutes ago')."""
    return f"<t:{int(ts)}:{style}>" if ts else "never"


def bar(done: int, total: int, width: int = 18) -> str:
    total = max(total, 1)
    filled = round(width * min(max(done, 0), total) / total)
    return "█" * filled + "░" * (width - filled)


async def reply(interaction: discord.Interaction, *args, **kwargs) -> None:
    """Respond or follow up, whichever is still allowed."""
    kwargs.setdefault("ephemeral", True)
    if interaction.response.is_done():
        await interaction.followup.send(*args, **kwargs)
    else:
        await interaction.response.send_message(*args, **kwargs)


# ── permission decorators for slash commands ──────────────────────────────────
from discord import app_commands  # noqa: E402


def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.client.settings.is_admin(interaction.user)

    return app_commands.check(predicate)


def leadership_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.client.settings.is_leadership(interaction.user)

    return app_commands.check(predicate)


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.client.settings.is_staff(interaction.user)

    return app_commands.check(predicate)
