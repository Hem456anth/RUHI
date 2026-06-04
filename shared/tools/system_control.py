"""System control — brightness, volume, app launch/close, WiFi, system info.

Ported from ``features/automation/system_control.py``: dropped the per-instance
scripts directory (out of scope for the split) and the ``SystemControl`` class
wrapper. These are now plain async functions consumed by Jarvis agent tools.

Cross-platform: Windows / Linux / macOS branches preserved.
"""
from __future__ import annotations

import asyncio
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil

from shared.tools.errors import ToolError

_OS = platform.system().lower()


# ── brightness ───────────────────────────────────────────────────────


async def set_brightness(level: int) -> bool:
    level = max(0, min(100, level))
    try:
        if _OS == "windows":
            import screen_brightness_control as sbc  # type: ignore[import-not-found]

            sbc.set_brightness(level)
        elif _OS == "linux":
            displays = subprocess.check_output(["xrandr", "--listmonitors"]).decode()
            names = [ln.split()[3] for ln in displays.splitlines()[1:] if ln]
            for d in names:
                subprocess.run(["xrandr", "--output", d, "--brightness", str(level / 100)])
        elif _OS == "darwin":
            script = (
                f'tell application "System Events" to tell appearance preferences '
                f'to set brightness to {level / 100}'
            )
            subprocess.run(["osascript", "-e", script])
        return True
    except Exception as e:
        raise ToolError(f"Brightness control failed: {e}", code="brightness")


# ── volume ───────────────────────────────────────────────────────────


async def set_volume(level: int) -> bool:
    level = max(0, min(100, level))
    try:
        if _OS == "windows":
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL  # type: ignore[import-not-found]
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore[import-not-found]

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            vol.SetMasterVolumeLevelScalar(level / 100, None)
        elif _OS == "linux":
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
        elif _OS == "darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
        return True
    except Exception as e:
        raise ToolError(f"Volume control failed: {e}", code="volume")


# ── apps ─────────────────────────────────────────────────────────────


async def launch_app(name: str) -> bool:
    try:
        if _OS == "windows":
            subprocess.Popen(f"start {name}", shell=True)
        elif _OS == "linux":
            subprocess.Popen([name])
        elif _OS == "darwin":
            subprocess.run(["open", "-a", name])
        return True
    except Exception as e:
        raise ToolError(f"Failed to launch {name}: {e}", code="launch")


async def close_app(name: str) -> int:
    closed = 0
    for proc in psutil.process_iter(["name"]):
        info_name = proc.info.get("name") or ""
        if name.lower() in info_name.lower():
            try:
                proc.terminate()
                closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return closed


# ── info ─────────────────────────────────────────────────────────────


@dataclass
class SystemInfo:
    os: str
    version: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    battery_percent: Optional[float]
    battery_plugged: Optional[bool]


async def get_system_info() -> SystemInfo:
    battery = psutil.sensors_battery()
    return SystemInfo(
        os=platform.system(),
        version=platform.version(),
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        battery_percent=battery.percent if battery else None,
        battery_plugged=battery.power_plugged if battery else None,
    )


# ── wifi (best-effort, often requires admin) ─────────────────────────


async def set_wifi(enable: bool) -> bool:
    try:
        if _OS == "windows":
            action = "enable" if enable else "disable"
            subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", action])
        elif _OS == "linux":
            subprocess.run(["nmcli", "radio", "wifi", "on" if enable else "off"])
        elif _OS == "darwin":
            subprocess.run(
                ["networksetup", "-setairportpower", "en0", "on" if enable else "off"]
            )
        return True
    except Exception as e:
        raise ToolError(f"WiFi toggle failed: {e}", code="wifi")
