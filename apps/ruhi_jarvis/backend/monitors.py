"""Periodic system-stats push loop.

Powers the live widgets on the JARVIS dashboard (CPU ring, RAM ring, battery,
disk). Runs as a background task started by the FastAPI lifespan; broadcasts
each tick to all connected WebSockets via a fan-out registry.

Design choices
--------------
- One single loop per process (not per-WS) so we don't multiply the work
  by the number of dashboard tabs open.
- Async ``Queue`` per subscriber so a slow client can't block the loop.
- Default interval is 2s — fast enough to feel live, slow enough to keep
  CPU overhead from the monitor itself negligible (~0%).
"""
from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass

from shared.tools.system_stats import system_stats


@dataclass
class MonitorEvent:
    cpu_percent: float
    memory_percent: float
    memory_used: str
    memory_total: str
    disk_percent: float
    battery_percent: float | None
    battery_plugged: bool | None

    def to_json(self) -> dict:
        return {
            "event": "monitor",
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used": self.memory_used,
            "memory_total": self.memory_total,
            "disk_percent": self.disk_percent,
            "battery_percent": self.battery_percent,
            "battery_plugged": self.battery_plugged,
        }


class MonitorHub:
    """Fan-out broadcaster: one producer loop, many WebSocket subscribers."""

    def __init__(self, interval: float = 2.0, queue_max: int = 8) -> None:
        self.interval = interval
        self._subscribers: set[asyncio.Queue[MonitorEvent]] = set()
        self._task: asyncio.Task | None = None
        self._queue_max = queue_max

    # ── lifecycle ─────────────────────────────────────────────────────
    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="monitor-hub")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    # ── subscribe API ─────────────────────────────────────────────────
    def subscribe(self) -> asyncio.Queue[MonitorEvent]:
        q: asyncio.Queue[MonitorEvent] = asyncio.Queue(maxsize=self._queue_max)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[MonitorEvent]) -> None:
        self._subscribers.discard(q)

    # ── producer ──────────────────────────────────────────────────────
    async def _run(self) -> None:
        while True:
            try:
                stats = await system_stats()
                event = MonitorEvent(
                    cpu_percent=stats.cpu_percent,
                    memory_percent=stats.memory_percent,
                    memory_used=stats.memory_used,
                    memory_total=stats.memory_total,
                    disk_percent=stats.disk_percent,
                    battery_percent=stats.battery_percent,
                    battery_plugged=stats.battery_plugged,
                )
                for q in list(self._subscribers):
                    # Drop oldest on overflow rather than blocking the loop.
                    if q.full():
                        with contextlib.suppress(asyncio.QueueEmpty):
                            q.get_nowait()
                    with contextlib.suppress(asyncio.QueueFull):
                        q.put_nowait(event)
            except Exception:
                # Never let a transient psutil hiccup kill the monitor.
                pass
            await asyncio.sleep(self.interval)
