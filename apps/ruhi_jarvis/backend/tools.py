"""Jarvis tool set.

Wider and more system-oriented than Chat: brightness, volume, system info,
app launch — the things a JARVIS-style dashboard is *for*. All wrapped as
``StructuredTool`` so the LangGraph ReAct agent can call them with typed
arguments.

The underlying implementations live in ``shared.tools.*``; this module is
just the wiring layer that decides which tools Jarvis exposes.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool

from shared.tools.app_launch import launch as _launch
from shared.tools.calendar import list_events
from shared.tools.news import get_news
from shared.tools.notes import make_note
from shared.tools.system_control import (
    close_app,
    get_system_info,
    set_brightness,
    set_volume,
    set_wifi,
)
from shared.tools.system_stats import system_stats
from shared.tools.weather import fetch_weather
from shared.tools.web_search import web_search


# ── adapters (async, return strings the LLM can quote back) ──────────


async def _t_stats() -> str:
    s = await system_stats()
    return s.to_sentence()


async def _t_sysinfo() -> str:
    i = await get_system_info()
    return (
        f"OS={i.os} {i.version}; CPU={i.cpu_percent}%; RAM={i.memory_percent}%; "
        f"disk={i.disk_percent}%; battery={i.battery_percent}% "
        f"({'plugged' if i.battery_plugged else 'on battery'})."
    )


async def _t_brightness(level: int) -> str:
    await set_brightness(level)
    return f"Brightness set to {level}%."


async def _t_volume(level: int) -> str:
    await set_volume(level)
    return f"Volume set to {level}%."


async def _t_wifi(enable: bool) -> str:
    await set_wifi(enable)
    return f"WiFi {'enabled' if enable else 'disabled'}."


async def _t_launch_app(name: str) -> str:
    await _launch(name)
    return f"Launched {name}."


async def _t_close_app(name: str) -> str:
    n = await close_app(name)
    return f"Closed {n} process(es) matching {name!r}."


async def _t_weather(city: str) -> str:
    return (await fetch_weather(city)).to_sentence()


async def _t_news(query: str | None = None, limit: int = 5) -> str:
    articles = await get_news(query=query, limit=limit)
    return "\n".join(f"- {a.title} ({a.source})" for a in articles) or "No news."


async def _t_search(query: str, limit: int = 5) -> str:
    results = await web_search(query, limit=limit)
    return "\n".join(f"- {r.title}: {r.snippet}" for r in results) or "No results."


async def _t_calendar(days_ahead: int = 0) -> str:
    events = await list_events(days_ahead=days_ahead)
    return "\n".join(f"- {e.summary} @ {e.start}" for e in events) or "No upcoming events."


async def _t_note(text: str) -> str:
    p = await make_note(text)
    return f"Saved note: {p}"


# ── public: the tool list passed to the agent ────────────────────────


def build_jarvis_tools() -> list[StructuredTool]:
    """Return the StructuredTool list for the Jarvis agent.

    Order matters only for the ReAct system prompt's "tools available" block;
    we put the system controls first because that's the dashboard's identity.
    """
    return [
        StructuredTool.from_function(
            coroutine=_t_stats,
            name="system_stats",
            description="Get current CPU, RAM, disk, and battery snapshot. No args.",
        ),
        StructuredTool.from_function(
            coroutine=_t_sysinfo,
            name="system_info",
            description="Get OS version and a fuller system snapshot. No args.",
        ),
        StructuredTool.from_function(
            coroutine=_t_brightness,
            name="set_brightness",
            description="Set screen brightness. Input: level (0-100).",
        ),
        StructuredTool.from_function(
            coroutine=_t_volume,
            name="set_volume",
            description="Set system volume. Input: level (0-100).",
        ),
        StructuredTool.from_function(
            coroutine=_t_wifi,
            name="set_wifi",
            description="Enable or disable WiFi. Input: enable (true/false).",
        ),
        StructuredTool.from_function(
            coroutine=_t_launch_app,
            name="launch_app",
            description=(
                "Launch an application by alias or executable name. "
                "Aliases include chrome, edge, notepad, calculator, paint, "
                "task manager, settings."
            ),
        ),
        StructuredTool.from_function(
            coroutine=_t_close_app,
            name="close_app",
            description="Terminate processes whose name contains the given string.",
        ),
        StructuredTool.from_function(
            coroutine=_t_weather,
            name="get_weather",
            description="Current weather for a city. Input: city name.",
        ),
        StructuredTool.from_function(
            coroutine=_t_news,
            name="get_news",
            description="Top headlines. Optional: query, limit.",
        ),
        StructuredTool.from_function(
            coroutine=_t_search,
            name="web_search",
            description="Search the web (Google CSE). Input: query.",
        ),
        StructuredTool.from_function(
            coroutine=_t_calendar,
            name="upcoming_events",
            description="List Google Calendar events. Optional: days_ahead.",
        ),
        StructuredTool.from_function(
            coroutine=_t_note,
            name="make_note",
            description="Save a quick text note. Input: text.",
        ),
    ]
