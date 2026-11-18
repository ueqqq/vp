"""Simple music player (Musico-style basics).

Requires: ffmpeg on the host + `yt-dlp` and `PyNaCl` in requirements.
Works for YouTube / many direct links. Queue is per-guild.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

import discord
from discord import app_commands
from discord.ext import commands

from core import config as cfg
from core.ui import embed, reply, success, error

log = logging.getLogger("castro.music")

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    url: str
    webpage_url: str
    duration: int | None
    requester: discord.Member


@dataclass
class GuildPlayer:
    voice: discord.VoiceClient | None = None
    queue: Deque[Track] = field(default_factory=deque)
    current: Track | None = None
    playing: bool = False


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await reply(interaction, embed=error("Not in voice", "Join a voice channel first, then try again."))
            return None
        player = self.get_player(interaction.guild_id)
        channel = interaction.user.voice.channel
        if player.voice and player.voice.is_connected():
            if player.voice.channel.id != channel.id:
                await player.voice.move_to(channel)
            return player.voice
        try:
            player.voice = await channel.connect(timeout=15, reconnect=True)
            return player.voice
        except Exception as exc:
            log.exception("voice connect failed")
            await reply(interaction, f"❌ Could not join voice: {exc}")
            return None

    def _extract(self, query: str) -> list[Track]:
        if yt_dlp is None:
            raise RuntimeError("yt-dlp is not installed")
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries") or [info]
            tracks = []
            for e in entries[:15]:  # safety limit for playlists
                if not e:
                    continue
                tracks.append(
                    Track(
                        title=e.get("title") or "Unknown",
                        url=e.get("url") or e.get("webpage_url"),
                        webpage_url=e.get("webpage_url") or e.get("url") or query,
                        duration=e.get("duration"),
                        requester=None,  # filled later
                    )
                )
            return tracks

    async def play_next(self, guild_id: int) -> None:
        player = self.get_player(guild_id)
        if not player.queue:
            player.current = None
            player.playing = False
            return
        track = player.queue.popleft()
        player.current = track
        player.playing = True

        def after_play(err):
            if err:
                log.error("player error: %s", err)
            asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)

        try:
            source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTS)
            player.voice.play(source, after=after_play)
        except Exception:
            log.exception("failed to start track")
            await self.play_next(guild_id)

    # ── slash commands ────────────────────────────────────────────────────────
    @app_commands.command(name="play", description="Play a song or add it to the queue")
    @app_commands.describe(query="Song name or URL")
    async def play(self, interaction: discord.Interaction, query: str):
        if yt_dlp is None:
            return await reply(interaction, "❌ Music is not available (yt-dlp missing).")
        voice = await self.ensure_voice(interaction)
        if voice is None:
            return
        await interaction.response.defer(ephemeral=True)
        try:
            tracks = await asyncio.to_thread(self._extract, query)
        except Exception as exc:
            return await interaction.followup.send(f"❌ Could not load: {exc}", ephemeral=True)
        if not tracks:
            return await interaction.followup.send("❌ Nothing found.", ephemeral=True)

        player = self.get_player(interaction.guild_id)
        for t in tracks:
            t.requester = interaction.user
            player.queue.append(t)

        first = tracks[0]
        msg = f"✅ Queued **{first.title}**"
        if len(tracks) > 1:
            msg += f" (+{len(tracks)-1} more)"
        await interaction.followup.send(msg, ephemeral=True)

        if not player.playing:
            await self.play_next(interaction.guild_id)

    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.voice or not player.playing:
            return await reply(interaction, embed=error("Nothing playing", "There is no track currently playing."))
        player.voice.stop()
        await reply(interaction, embed=success("Skipped", "Playing the next track (if any)."))

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        if player.voice and player.voice.is_playing():
            player.voice.stop()
        player.playing = False
        player.current = None
        await reply(interaction, embed=success("Stopped", "Playback stopped and the queue was cleared."))

    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if player.voice and player.voice.is_playing():
            player.voice.pause()
            await reply(interaction, embed=success("Paused", "Playback is paused. Use `/resume` to continue."))
        else:
            await reply(interaction, embed=error("Nothing playing", "There is no track currently playing."))

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if player.voice and player.voice.is_paused():
            player.voice.resume()
            await reply(interaction, embed=success("Resumed", "Playback continues."))
        else:
            await reply(interaction, "Nothing is paused.")

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current and not player.queue:
            return await reply(interaction, embed=error("Empty queue", "Nothing is queued right now."))
        lines = []
        if player.current:
            lines.append(f"**Now:** {player.current.title}")
        for i, t in enumerate(list(player.queue)[:12], 1):
            lines.append(f"`{i}.` {t.title}")
        if len(player.queue) > 12:
            lines.append(f"… and {len(player.queue) - 12} more")
        await reply(interaction, embed=embed("Queue", "\n".join(lines), cfg.BLUE))

    @app_commands.command(name="nowplaying", description="Show the track that is playing")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current:
            return await reply(interaction, embed=error("Nothing playing", "There is no track currently playing."))
        t = player.current
        em = embed("Now Playing", f"**{t.title}**\nRequested by {t.requester.mention}", cfg.RED)
        if t.webpage_url:
            em.url = t.webpage_url
        await reply(interaction, embed=em)

    @app_commands.command(name="leave", description="Disconnect the bot from voice")
    async def leave(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        player.current = None
        player.playing = False
        if player.voice and player.voice.is_connected():
            await player.voice.disconnect()
            player.voice = None
        await reply(interaction, embed=success("Disconnected", "Left the voice channel."))


async def setup(bot):
    await bot.add_cog(Music(bot))
