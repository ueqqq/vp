"""Castro: Discord bot for the Cuba nation on DiplomaticaMC. Run with: python bot.py"""

from __future__ import annotations

import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.settings import Settings
from core.store import Store
from core.ui import reply

log = logging.getLogger("castro")

EXTENSIONS = ["cogs.votes", "cogs.hub", "cogs.applications", "cogs.support", "cogs.nation",
              "cogs.citizens", "cogs.government", "cogs.diplomacy", "cogs.quotes", "cogs.fun",
              "cogs.music", "cogs.admin"]


class CastroBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # welcome messages + granting roles. Enable "Server Members Intent" in the dev portal.
        # message_content is deliberately NOT requested: everything here is slash commands and buttons.
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None,
                         activity=discord.Activity(type=discord.ActivityType.watching,
                                                   name=f"over {cfg.NATION_NAME} {cfg.NATION_FLAG}"))
        self.store = Store(cfg.DATA_DIR)
        self.settings = Settings(self.store)

    def lang(self, user_id: int) -> str:
        return self.store.data("users", {}).get(str(user_id), {}).get("lang", "en")

    async def setup_hook(self) -> None:
        await self.store.start()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        self.tree.on_error = self.on_tree_error
        meta = self.store.data("meta", {})
        if meta.get("synced_version") != cfg.VERSION:  # only re-sync when commands could have changed
            try:
                count = await self.sync_commands()
                meta["synced_version"] = cfg.VERSION
                self.store.save("meta")
                log.info("synced %s commands", count)
            except discord.HTTPException:
                log.exception("command sync failed; run /castro sync later")

    async def sync_commands(self) -> int:
        if cfg.GUILD_ID:
            guild = discord.Object(id=cfg.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            return len(await self.tree.sync(guild=guild))
        return len(await self.tree.sync())

    async def on_ready(self) -> None:
        log.info("logged in as %s in %s server(s)", self.user, len(self.guilds))

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):
            text = "❌ You don't have permission to use that."
        else:
            log.error("command %s failed", getattr(interaction.command, "name", "?"), exc_info=error)
            text = "❌ Something went wrong. Please try again in a moment."
        try:
            await reply(interaction, text)
        except discord.HTTPException:
            pass

    async def close(self) -> None:
        await self.store.close()  # flush saved data before shutting down
        await super().close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if not cfg.TOKEN:
        sys.exit("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and add your token.")
    CastroBot().run(cfg.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
