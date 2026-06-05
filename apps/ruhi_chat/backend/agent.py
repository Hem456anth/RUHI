"""LangChain conversational agent for RUHI Chat.

The agent always sees **English** input (the pipeline translates inbound
Indian-language text first), and produces English output (the pipeline
translates outbound text). Keeping the agent monolingual:

  - keeps tool prompts and reasoning crisp,
  - lets a single LLM handle all 10 target languages well,
  - decouples agent quality from Mayura translation quality (which is
    Sarvam's strongest model anyway).

The tool set is intentionally compact: chat users want "what's the weather",
"find news about X", "look this up" — not system control. Calendar/notes
are exposed for personal-assistant flavor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from shared.llm import get_llm
from shared.tools.calendar import list_events
from shared.tools.news import get_news
from shared.tools.notes import make_note
from shared.tools.weather import fetch_weather
from shared.tools.web_search import web_search

SYSTEM_PROMPT = (
    "You are RUHI, a helpful multilingual Indian assistant. "
    "You are currently reasoning in English; the surrounding pipeline handles "
    "translation to and from the user's language. Keep answers concise, "
    "friendly, and culturally aware. Use tools when you need fresh facts; "
    "answer from your own knowledge otherwise. Never fabricate tool outputs."
)


# ── tool adapters ────────────────────────────────────────────────────
# StructuredTool needs sync wrappers around the async shared tools, plus
# argument schemas LangChain can introspect.


async def _tool_weather(city: str) -> str:
    report = await fetch_weather(city)
    return report.to_sentence()


async def _tool_news(query: str | None = None, country: str = "in", limit: int = 5) -> str:
    articles = await get_news(query=query, country=country, limit=limit)
    if not articles:
        return "No news articles found."
    return "\n".join(f"- {a.title} ({a.source}) [{a.url}]" for a in articles)


async def _tool_web_search(query: str, limit: int = 5) -> str:
    results = await web_search(query, limit=limit)
    if not results:
        return "No search results."
    return "\n".join(f"- {r.title}: {r.snippet} [{r.url}]" for r in results)


async def _tool_calendar(days_ahead: int = 0) -> str:
    events = await list_events(days_ahead=days_ahead)
    if not events:
        return "No upcoming events."
    return "\n".join(f"- {e.summary} at {e.start}" for e in events)


async def _tool_make_note(text: str) -> str:
    path = await make_note(text)
    return f"Saved note: {path}"


def _build_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            coroutine=_tool_weather,
            name="get_weather",
            description="Get current weather for an Indian or global city. Input: city name.",
        ),
        StructuredTool.from_function(
            coroutine=_tool_news,
            name="get_news",
            description=(
                "Get top news headlines. Optional: query (search term), "
                "country (ISO code, default 'in'), limit."
            ),
        ),
        StructuredTool.from_function(
            coroutine=_tool_web_search,
            name="web_search",
            description="Search the web via Google for current information. Input: query.",
        ),
        StructuredTool.from_function(
            coroutine=_tool_calendar,
            name="upcoming_events",
            description=(
                "List the user's upcoming Google Calendar events. "
                "Optional: days_ahead (0 = today only)."
            ),
        ),
        StructuredTool.from_function(
            coroutine=_tool_make_note,
            name="make_note",
            description="Save a quick text note for the user. Input: text content.",
        ),
    ]


# ── agent ────────────────────────────────────────────────────────────


@dataclass
class AgentResponse:
    reply: str
    tool_calls: list[str]  # names of tools the agent invoked, in order


def _extract_text(content: Any) -> str:
    """Normalize ``AIMessage.content`` to plain text.

    LangChain 1.x with Gemini returns ``content`` as a list of structured
    blocks like ``[{"type": "text", "text": "...", "extras": {...}}]``; older
    OpenAI/Ollama paths return plain strings. We accept both and concatenate
    text blocks in order, ignoring non-text parts (thinking, signatures,
    citations, etc.).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()
    return str(content)


class ChatAgent:
    """One agent instance per process; per-session history is held by the caller."""

    def __init__(self, *, llm: Any | None = None, tools: list[StructuredTool] | None = None) -> None:
        self.llm = llm or get_llm()  # default chat provider from settings
        self.tools = tools if tools is not None else _build_tools()
        self.graph = create_react_agent(
            self.llm,
            self.tools,
            prompt=SYSTEM_PROMPT,
        )

    async def respond(
        self,
        user_message_en: str,
        *,
        history: InMemoryChatMessageHistory | None = None,
    ) -> AgentResponse:
        """Run one agent turn. ``user_message_en`` MUST already be English."""
        history = history or InMemoryChatMessageHistory()
        history.add_user_message(user_message_en)

        messages = [SystemMessage(SYSTEM_PROMPT), *history.messages]
        result = await self.graph.ainvoke({"messages": messages})

        all_msgs = result.get("messages", [])
        reply = ""
        tool_calls: list[str] = []
        for m in all_msgs:
            if isinstance(m, AIMessage):
                if getattr(m, "tool_calls", None):
                    tool_calls.extend(tc.get("name", "?") for tc in m.tool_calls)
                if m.content:
                    reply = _extract_text(m.content)

        history.add_ai_message(reply)
        return AgentResponse(reply=reply, tool_calls=tool_calls)
