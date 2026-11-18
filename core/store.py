"""Tiny JSON persistence layer.

Fixes over the old data manager:
  * the flush loop is started from inside the running event loop (the old one never started)
  * writes are atomic (temp file + os.replace) so a crash can't leave half a file
  * a corrupt file is moved aside instead of silently wiping your data
  * everything is flushed on shutdown
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("castro.store")


class Store:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {}
        self._dirty: set[str] = set()
        self._task: asyncio.Task | None = None

    # ── access ────────────────────────────────────────────────────────────────
    def data(self, name: str, default: Any = None) -> Any:
        """Return the live object for `name`. Mutate it, then call save(name)."""
        if name not in self._data:
            self._data[name] = self._load(name, {} if default is None else default)
        return self._data[name]

    def save(self, name: str) -> None:
        self._dirty.add(name)

    # ── disk ──────────────────────────────────────────────────────────────────
    def _path(self, name: str) -> Path:
        return self.dir / f"{name}.json"

    def _load(self, name: str, default: Any) -> Any:
        path = self._path(name)
        if not path.exists():
            return copy.deepcopy(default)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            backup = path.with_name(f"{name}.corrupt-{int(time.time())}.json")
            log.error("%s unreadable (%s); moving it to %s and starting fresh", path.name, exc, backup.name)
            try:
                path.replace(backup)
            except OSError:
                pass
            return copy.deepcopy(default)

    def _write(self, name: str, payload: str) -> None:
        path = self._path(name)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)

    def flush_sync(self) -> None:
        for name in list(self._dirty):
            self._dirty.discard(name)
            try:
                self._write(name, json.dumps(self._data[name], indent=2, ensure_ascii=False))
            except OSError as exc:
                log.error("could not save %s: %s", name, exc)
                self._dirty.add(name)

    async def flush(self) -> None:
        for name in list(self._dirty):
            self._dirty.discard(name)
            # snapshot on the event loop so the thread never sees a half-mutated object
            payload = json.dumps(self._data[name], indent=2, ensure_ascii=False)
            try:
                await asyncio.to_thread(self._write, name, payload)
            except OSError as exc:
                log.error("could not save %s: %s", name, exc)
                self._dirty.add(name)

    # ── lifecycle ─────────────────────────────────────────────────────────────
    async def start(self, interval: float = 10.0) -> None:
        async def loop() -> None:
            while True:
                await asyncio.sleep(interval)
                await self.flush()

        self._task = asyncio.create_task(loop())

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        await self.flush()
