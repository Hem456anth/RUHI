"""Application launch — cross-platform, no hard-coded paths.

Resolves common app aliases (chrome, edge, notepad, calc...) per OS, then
falls back to ``shared.tools.system_control.launch_app`` for arbitrary names.
"""
from __future__ import annotations

import platform

from shared.tools.errors import ToolError
from shared.tools.system_control import launch_app as _launch

_OS = platform.system().lower()

_WINDOWS_ALIASES = {
    "chrome": "chrome",
    "edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:",
    "msi center": "MSI Center",
    "explorer": "explorer",
}
_MAC_ALIASES = {
    "chrome": "Google Chrome",
    "safari": "Safari",
    "calculator": "Calculator",
    "notes": "Notes",
    "terminal": "Terminal",
}
_LINUX_ALIASES = {
    "chrome": "google-chrome",
    "firefox": "firefox",
    "calculator": "gnome-calculator",
    "terminal": "gnome-terminal",
    "files": "nautilus",
}


def _resolve(name: str) -> str:
    n = name.lower().strip()
    table = (
        _WINDOWS_ALIASES if _OS == "windows"
        else _MAC_ALIASES if _OS == "darwin"
        else _LINUX_ALIASES
    )
    return table.get(n, name)


async def launch(app_name: str) -> bool:
    target = _resolve(app_name)
    try:
        return await _launch(target)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to launch {app_name!r}: {e}", code="launch")
