"""System stats — CPU, RAM, battery, disk. Used by Jarvis dashboard widgets.

Ported from ``Ruhi/features/system_stats.py`` — replaced pyttsx3 coupling
and string formatting with a structured dataclass the dashboard can render.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import psutil


def _human_bytes(n: int) -> str:
    if n == 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = min(int(math.floor(math.log(n, 1024))), len(units) - 1)
    return f"{round(n / (1024 ** i), 2)} {units[i]}"


@dataclass
class SystemStats:
    cpu_percent: float
    memory_used: str
    memory_total: str
    memory_percent: float
    disk_percent: float
    battery_percent: float | None
    battery_plugged: bool | None

    def to_sentence(self) -> str:
        bat = (
            f", battery {self.battery_percent}% {'plugged' if self.battery_plugged else 'on battery'}"
            if self.battery_percent is not None
            else ""
        )
        return (
            f"CPU {self.cpu_percent}%, RAM {self.memory_used} / "
            f"{self.memory_total} ({self.memory_percent}%), disk {self.disk_percent}%{bat}."
        )

    def as_dict(self) -> dict:
        return asdict(self)


async def system_stats() -> SystemStats:
    vm = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    return SystemStats(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_used=_human_bytes(vm.used),
        memory_total=_human_bytes(vm.total),
        memory_percent=vm.percent,
        disk_percent=psutil.disk_usage("/").percent,
        battery_percent=battery.percent if battery else None,
        battery_plugged=battery.power_plugged if battery else None,
    )
