"""Phase 2A smoke test — runs the full Chat pipeline end-to-end with a fake
Sarvam client and a fake agent. Verifies wiring without spending any credits.

Run:
    .venv/Scripts/python.exe apps/ruhi_chat/backend/tests/smoke_test.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

# Make repo root importable when run as a script.
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from apps.ruhi_chat.backend.agent import ChatAgent, AgentResponse
from apps.ruhi_chat.backend.pipeline import ChatPipeline
from apps.ruhi_chat.backend.sarvam import LanguageId


# ── fakes ────────────────────────────────────────────────────────────


class FakeSarvam:
    """Stand-in that records calls so we can assert pipeline shape."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def identify_language(self, text: str) -> LanguageId:
        self.calls.append(f"lid({text[:20]!r})")
        # Pretend Telugu unless the string is ASCII.
        if all(ord(c) < 128 for c in text):
            return LanguageId(language_code="en-IN", script_code=None, iso_code="en")
        return LanguageId(language_code="te-IN", script_code="Telu", iso_code="te")

    async def translate(self, text: str, *, source: str, target: str, mode: str = "formal") -> str:
        self.calls.append(f"translate({source}->{target})")
        if source.startswith("te") and target.startswith("en"):
            return f"[EN] {text}"
        if source.startswith("en") and target.startswith("te"):
            return f"[TE] {text}"
        return text

    async def transcribe(self, audio: bytes, *, language=None, filename="audio.wav"):
        self.calls.append(f"asr({len(audio)} bytes)")
        from shared.voice.stt import Transcript

        return Transcript(text="నాకు హైదరాబాద్ వాతావరణం చెప్పు", language="te-IN", confidence=0.9)

    async def synthesize(self, text: str, *, language: str, speaker=None, pace=1.0) -> bytes:
        self.calls.append(f"tts({language}, {len(text)} chars)")
        return b"RIFFFAKEWAV"


@dataclass
class _FakeGraph:
    """Mimics LangGraph's create_react_agent.ainvoke shape."""

    async def ainvoke(self, payload):
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content="The weather in Hyderabad is sunny, 32°C.")]}


class FakeAgent(ChatAgent):
    def __init__(self) -> None:
        # Skip parent __init__ — we don't want to instantiate a real LLM.
        self.graph = _FakeGraph()

    async def respond(self, user_message_en, *, history=None):
        # Bypass the real path; record the English we got and return a fixed reply.
        return AgentResponse(
            reply="The weather in Hyderabad is sunny, 32°C.",
            tool_calls=["get_weather"],
        )


# ── tests ────────────────────────────────────────────────────────────


async def test_text_turn_telugu() -> None:
    sarvam = FakeSarvam()
    pipe = ChatPipeline(sarvam=sarvam, agent=FakeAgent())  # type: ignore[arg-type]

    turn = await pipe.run(text="నాకు హైదరాబాద్ వాతావరణం చెప్పు", want_audio=False)

    assert turn.detected_language == "te-IN", turn.detected_language
    assert turn.user_text_en.startswith("[EN] "), turn.user_text_en
    assert turn.reply_en.startswith("The weather"), turn.reply_en
    assert turn.reply_native.startswith("[TE] "), turn.reply_native
    assert turn.reply_audio is None
    assert turn.tool_calls == ["get_weather"]
    assert "lid" in sarvam.calls[0]
    assert any("translate(te-IN->en-IN)" in c for c in sarvam.calls)
    assert any("translate(en-IN->te-IN)" in c for c in sarvam.calls)
    print("[OK] text_turn_telugu       :", sarvam.calls)


async def test_text_turn_english_skips_translation() -> None:
    sarvam = FakeSarvam()
    pipe = ChatPipeline(sarvam=sarvam, agent=FakeAgent())  # type: ignore[arg-type]

    turn = await pipe.run(text="What is the weather in Hyderabad?", want_audio=False)

    assert turn.detected_language == "en-IN"
    assert turn.user_text_en == turn.user_text_native, "no-op translation expected"
    assert turn.reply_native == turn.reply_en
    assert not any("translate(" in c for c in sarvam.calls), sarvam.calls
    print("[OK] english_skips_translation:", sarvam.calls)


async def test_voice_turn_with_audio_out() -> None:
    sarvam = FakeSarvam()
    pipe = ChatPipeline(sarvam=sarvam, agent=FakeAgent())  # type: ignore[arg-type]

    turn = await pipe.run(audio=b"\x00\x00\x00\x00" * 10, want_audio=True, speaker="ritu")

    assert turn.input_mode == "voice"
    assert turn.detected_language == "te-IN"
    assert turn.reply_audio == b"RIFFFAKEWAV"
    assert any("asr(" in c for c in sarvam.calls)
    assert any("tts(te-IN" in c for c in sarvam.calls)
    print("[OK] voice_turn_with_audio_out:", sarvam.calls)


async def test_sarvam_cache_dedup() -> None:
    """Identical Sarvam calls must hit the cache, not the network."""
    from shared.cache import get_sarvam_cache

    cache = get_sarvam_cache()
    cache.clear("translate")
    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return {"translated_text": "ok"}

    for _ in range(5):
        await cache.get_or_set(
            endpoint="translate",
            language="te-IN->en-IN",
            payload={"input": "hello"},
            fetch=fake_fetch,
        )
    assert calls["n"] == 1, f"cache leak: {calls['n']} fetches"
    print(f"[OK] cache dedup            : 5 lookups, {calls['n']} fetch ({1.0 - calls['n']/5:.0%} credit savings)")


async def main() -> None:
    print("--- Phase 2A smoke test (no Sarvam credits used) ---")
    await test_text_turn_telugu()
    await test_text_turn_english_skips_translation()
    await test_voice_turn_with_audio_out()
    await test_sarvam_cache_dedup()
    print("\n=== ALL GREEN ===")


if __name__ == "__main__":
    asyncio.run(main())
