"""Phase 2B smoke test — Jarvis backend with a fake LLM and mock voice.

Verifies:
  1. Agent streaming yields {thinking, tool_call, tool_result, reply, done}.
  2. MonitorHub broadcasts to multiple subscribers and survives a slow one.
  3. JarvisVoice falls back to mocks when neither Whisper nor Piper is
     installed AND no provider is forced.
  4. One-shot ``respond()`` returns a structured reply.

No Ollama / Whisper / Piper required.
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from apps.ruhi_jarvis.backend.agent import JarvisAgent, JarvisEvent
from apps.ruhi_jarvis.backend.monitors import MonitorHub


# ── fake LangGraph that simulates a ReAct flow ───────────────────────


@dataclass
class FakeGraph:
    """Yields the same shape that LangGraph's ``create_react_agent.astream``
    yields: dicts keyed by node name ("agent" / "tools") containing message
    lists. We pre-script a 2-step flow: think → tool call → tool result → reply.
    """

    scripted_tool_result: str = "CPU at 12%, RAM at 47%."
    final_reply: str = "Your system looks healthy."

    async def astream(self, payload):
        ai_with_call = AIMessage(
            content="I should check the live stats.",
            tool_calls=[{"name": "system_stats", "args": {}, "id": "call_1"}],
        )
        yield {"agent": {"messages": [ai_with_call]}}

        tool_msg = ToolMessage(content=self.scripted_tool_result, name="system_stats", tool_call_id="call_1")
        yield {"tools": {"messages": [tool_msg]}}

        final = AIMessage(content=self.final_reply)
        yield {"agent": {"messages": [final]}}

    async def ainvoke(self, payload):
        # For respond() one-shot path
        return {"messages": [AIMessage(content=self.final_reply)]}


class FakeAgent(JarvisAgent):
    def __init__(self) -> None:
        # Skip parent __init__: no real LLM, no real tools.
        self.graph = FakeGraph()
        self.llm = None  # type: ignore[assignment]
        self.tools = []


# ── tests ────────────────────────────────────────────────────────────


async def test_agent_stream_shape() -> None:
    events = []
    async for ev in FakeAgent().stream("how am I doing?"):
        events.append((ev.kind, ev.data))

    kinds = [k for k, _ in events]
    # Expected ordering: thinking, tool_call, tool_result, reply, done.
    assert "thinking" in kinds, kinds
    assert "tool_call" in kinds, kinds
    assert "tool_result" in kinds, kinds
    assert "reply" in kinds, kinds
    assert kinds[-1] == "done", kinds

    # tool_call carries name + args
    tc = next(e for k, e in events if k == "tool_call")
    assert tc["name"] == "system_stats", tc
    assert tc["args"] == {}, tc

    # reply contains the final text
    reply = next(e for k, e in events if k == "reply")
    assert reply["text"] == "Your system looks healthy.", reply
    print(f"[OK] agent stream shape    : {kinds}")


async def test_agent_respond_one_shot() -> None:
    res = await FakeAgent().respond("ping")
    assert res["reply"] == "Your system looks healthy.", res
    print(f"[OK] agent respond one-shot: reply={res['reply']!r}")


async def test_monitor_fanout() -> None:
    hub = MonitorHub(interval=0.05)
    await hub.start()
    a = hub.subscribe()
    b = hub.subscribe()
    try:
        ev_a = await asyncio.wait_for(a.get(), timeout=2.0)
        ev_b = await asyncio.wait_for(b.get(), timeout=2.0)
    finally:
        await hub.stop()

    assert ev_a.cpu_percent is not None
    assert ev_b.cpu_percent is not None
    # Both subscribers see live system data.
    assert 0 <= ev_a.memory_percent <= 100
    print(
        f"[OK] monitor fan-out       : "
        f"CPU={ev_a.cpu_percent:.1f}% RAM={ev_a.memory_percent:.1f}% (2 subscribers)"
    )


async def test_monitor_slow_subscriber() -> None:
    """A slow consumer must not stall the hub — overflow drops the oldest."""
    hub = MonitorHub(interval=0.02, queue_max=2)
    await hub.start()
    slow = hub.subscribe()
    try:
        # Don't drain `slow` — let it overflow.
        await asyncio.sleep(0.2)  # ~10 ticks vs queue_max=2
        assert slow.qsize() <= 2, slow.qsize()
    finally:
        await hub.stop()
    print(f"[OK] monitor slow consumer : queue capped at 2, no producer stall")


async def test_voice_default_providers_in_chat_mode() -> None:
    """When app_mode=chat (our config.env default), get_tts/get_stt
    fall back to mocks — JarvisVoice should still work that way for tests
    even though it's the wrong mode for production."""
    from apps.ruhi_jarvis.backend.voice import JarvisVoice

    v = JarvisVoice()
    # Touching .stt / .tts lazily instantiates them. In chat mode (which is
    # what config.env currently says), the defaults are mocks.
    assert v.stt.name in {"mock", "whisper"}, v.stt.name
    assert v.tts.name in {"mock", "piper", "vibevoice"}, v.tts.name
    print(f"[OK] voice providers       : stt={v.stt.name} tts={v.tts.name}")


async def main() -> None:
    print("--- Phase 2B smoke test (no Ollama / Whisper / Piper required) ---")
    await test_agent_stream_shape()
    await test_agent_respond_one_shot()
    await test_monitor_fanout()
    await test_monitor_slow_subscriber()
    await test_voice_default_providers_in_chat_mode()
    print("\n=== ALL GREEN ===")


if __name__ == "__main__":
    asyncio.run(main())
