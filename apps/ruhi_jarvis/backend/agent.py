"""LangGraph ReAct agent for RUHI Jarvis — with visible thinking.

Difference from Chat's agent: the JARVIS dashboard's *point* is that you see
the agent reason. So instead of just returning a final reply, we expose a
streaming method that emits structured events the WebSocket can forward to
the dashboard in real time:

    {event: "thinking", token: "I need to check the weather…"}
    {event: "tool_call", name: "get_weather", args: {"city": "Hyderabad"}}
    {event: "tool_result", name: "get_weather", result: "Sunny, 32°C"}
    {event: "reply", text: "It's sunny and 32°C in Hyderabad."}
    {event: "done"}

The agent is monolingual English (no translation pipeline like Chat) and
defaults to Ollama (Mistral 7B) for full local-first operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from apps.ruhi_jarvis.backend.tools import build_jarvis_tools
from shared.config import settings
from shared.llm import get_llm

SYSTEM_PROMPT = (
    "You are JARVIS, a concise, capable assistant running locally on the user's "
    "machine. You have tools for system control, system info, web lookup, "
    "calendar, news, and notes. Prefer tools for fresh facts and actions; "
    "answer from knowledge for general questions. Keep responses short — the "
    "user reads them on a dashboard alongside live system widgets."
)


# ── streamed events ──────────────────────────────────────────────────


@dataclass
class JarvisEvent:
    kind: str           # "thinking" | "tool_call" | "tool_result" | "reply" | "done" | "error"
    data: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {"event": self.kind, **self.data}


def _extract_text(content: Any) -> str:
    """Normalize ``AIMessage.content`` to plain text.

    Gemini / Anthropic in LangChain 1.x return content as a list of
    structured blocks (``[{"type":"text","text":"..."}]``); Ollama and
    older OpenAI paths return a plain string. We accept both, ignore
    non-text blocks (reasoning signatures, citations, tool-call args).
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


# ── agent ────────────────────────────────────────────────────────────


class JarvisAgent:
    def __init__(
        self,
        *,
        llm: Any | None = None,
        tools: list[StructuredTool] | None = None,
    ) -> None:
        # Jarvis defaults to whatever ``RUHI_JARVIS_LLM_PROVIDER`` says (ollama).
        # ``get_llm()`` already picks the right provider based on app mode,
        # but Jarvis can run inside the same process as the Chat dev tests,
        # so we pin the provider explicitly.
        self.llm = llm or get_llm(settings.jarvis_llm_provider)
        self.tools = tools if tools is not None else build_jarvis_tools()
        self.graph = create_react_agent(self.llm, self.tools, prompt=SYSTEM_PROMPT)

    # ── one-shot (no streaming) — useful for HTTP POST /jarvis/text ─
    async def respond(
        self,
        user_message: str,
        *,
        history: InMemoryChatMessageHistory | None = None,
    ) -> dict[str, Any]:
        history = history or InMemoryChatMessageHistory()
        history.add_user_message(user_message)
        messages = [SystemMessage(SYSTEM_PROMPT), *history.messages]
        result = await self.graph.ainvoke({"messages": messages})

        reply = ""
        tool_calls: list[str] = []
        for m in result.get("messages", []):
            if isinstance(m, AIMessage):
                if getattr(m, "tool_calls", None):
                    tool_calls.extend(tc.get("name", "?") for tc in m.tool_calls)
                if m.content:
                    reply = _extract_text(m.content)
        history.add_ai_message(reply)
        return {"reply": reply, "tool_calls": tool_calls}

    # ── streamed (the JARVIS-y path) ─────────────────────────────────
    async def stream(
        self,
        user_message: str,
        *,
        history: InMemoryChatMessageHistory | None = None,
    ) -> AsyncIterator[JarvisEvent]:
        """Yield ``JarvisEvent`` objects as the agent reasons.

        Implementation note: we drive the graph with ``astream`` (per-step
        snapshots) rather than ``astream_events`` (low-level token events).
        Per-step is enough granularity for "show me what the agent is doing"
        and is robust across LangGraph versions.
        """
        history = history or InMemoryChatMessageHistory()
        history.add_user_message(user_message)
        messages = [SystemMessage(SYSTEM_PROMPT), *history.messages]

        seen_msg_ids: set[str] = set()
        final_reply = ""

        try:
            async for step in self.graph.astream({"messages": messages}):
                # step is e.g. {"agent": {"messages": [...]}} or {"tools": {"messages": [...]}}
                for node, payload in step.items():
                    for m in payload.get("messages", []):
                        mid = getattr(m, "id", None) or id(m)
                        if mid in seen_msg_ids:
                            continue
                        seen_msg_ids.add(mid)

                        if isinstance(m, AIMessage):
                            # If the LLM picked tools, emit one tool_call per call.
                            for tc in getattr(m, "tool_calls", None) or []:
                                yield JarvisEvent(
                                    "tool_call",
                                    {"name": tc.get("name"), "args": tc.get("args", {})},
                                )
                            content = _extract_text(m.content) if m.content else ""
                            if content:
                                # Distinguish internal reasoning (intermediate AI
                                # messages between tool calls) from the final
                                # reply. The last AI message without tool_calls
                                # is the reply; everything else is "thinking".
                                if getattr(m, "tool_calls", None):
                                    yield JarvisEvent("thinking", {"text": content})
                                else:
                                    final_reply = content
                                    yield JarvisEvent("reply", {"text": content})
                        elif isinstance(m, ToolMessage):
                            yield JarvisEvent(
                                "tool_result",
                                {"name": m.name, "result": str(m.content)},
                            )
        except Exception as e:
            yield JarvisEvent("error", {"detail": f"{type(e).__name__}: {e}"})
            return

        history.add_ai_message(final_reply)
        yield JarvisEvent("done", {})
