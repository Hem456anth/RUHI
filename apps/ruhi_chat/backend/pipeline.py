"""End-to-end Chat pipeline.

Orchestrates the seven stages of a RUHI Chat turn:

    [audio?] ──► ASR ──► LID ──► NMT(src→en) ──► Agent ──► NMT(en→src) ──► TTS ──► [audio?]
                                                              │
                                                              └─ also returned as text

Text-only input skips ASR. Caller may opt out of TTS to save credits when only
text output is needed.

Every Sarvam leg is cached (see ``shared.cache.sarvam``); two identical turns
cost the same as one. With a 1000-credit dev budget, that's the difference
between "build a product" and "burn out the key on Tuesday".

Usage
-----
>>> pipe = ChatPipeline()
>>> async def go():
...     turn = await pipe.run(text="నాకు హైదరాబాద్ వాతావరణం చెప్పు", want_audio=False)
...     print(turn.reply_native, turn.detected_language, turn.tool_calls)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from langchain_core.chat_history import InMemoryChatMessageHistory

from apps.ruhi_chat.backend.agent import ChatAgent
from apps.ruhi_chat.backend.sarvam import SarvamClient, to_bcp47

InputMode = Literal["text", "voice"]


@dataclass
class TurnResult:
    detected_language: str        # BCP-47, e.g. "te-IN" — "en-IN" if direct English
    user_text_native: str         # raw user input in the detected language
    user_text_en: str             # English translation given to the agent
    reply_en: str                 # agent output (English)
    reply_native: str             # translated back into detected language
    reply_audio: bytes | None     # TTS bytes, or None if want_audio=False
    tool_calls: list[str] = field(default_factory=list)
    input_mode: InputMode = "text"


class ChatPipeline:
    """Stateless orchestrator. Sessions are external (per-WS-connection)."""

    def __init__(
        self,
        *,
        sarvam: SarvamClient | None = None,
        agent: ChatAgent | None = None,
        agent_language: str = "en-IN",
    ) -> None:
        self.sarvam = sarvam or SarvamClient()
        self.agent = agent or ChatAgent()
        self.agent_language = agent_language

    # ── public API ────────────────────────────────────────────────────
    async def run(
        self,
        *,
        text: str | None = None,
        audio: bytes | None = None,
        history: InMemoryChatMessageHistory | None = None,
        want_audio: bool = False,
        speaker: str | None = None,
        hint_language: str | None = None,
    ) -> TurnResult:
        if not (text or audio):
            raise ValueError("ChatPipeline.run requires text= or audio=.")

        input_mode: InputMode = "voice" if audio else "text"

        # 1. ASR (audio only)
        if audio is not None:
            transcript = await self.sarvam.transcribe(audio, language=hint_language)
            user_text_native = transcript.text
            asr_lang = transcript.language
        else:
            user_text_native = text or ""
            asr_lang = hint_language

        # 2. Language ID (skip if ASR already gave us one; skip if obviously English)
        if asr_lang and asr_lang != "auto":
            detected = to_bcp47(asr_lang)
        else:
            lid = await self.sarvam.identify_language(user_text_native)
            detected = lid.language_code or self.agent_language

        # 3. Translate user → English (no-op if already English)
        if detected.startswith("en"):
            user_text_en = user_text_native
        else:
            user_text_en = await self.sarvam.translate(
                user_text_native, source=detected, target=self.agent_language
            )

        # 4. Agent
        agent_resp = await self.agent.respond(user_text_en, history=history)
        reply_en = agent_resp.reply

        # 5. Translate reply → native (no-op if already English)
        if detected.startswith("en"):
            reply_native = reply_en
        else:
            reply_native = await self.sarvam.translate(
                reply_en, source=self.agent_language, target=detected
            )

        # 6. TTS (optional)
        reply_audio: bytes | None = None
        if want_audio:
            reply_audio = await self.sarvam.synthesize(
                reply_native, language=detected, speaker=speaker
            )

        return TurnResult(
            detected_language=detected,
            user_text_native=user_text_native,
            user_text_en=user_text_en,
            reply_en=reply_en,
            reply_native=reply_native,
            reply_audio=reply_audio,
            tool_calls=agent_resp.tool_calls,
            input_mode=input_mode,
        )
