"""Offline voice I/O for Jarvis.

Thin wrapper that owns one ``STTProvider`` and one ``TTSProvider`` chosen by
``shared.config.settings`` (which reads ``JARVIS_STT_PROVIDER`` /
``JARVIS_TTS_PROVIDER``). The shared layer does the heavy lifting; this module
is just a stable, narrow surface for the WebSocket handler.

No cloud fallback: by spec, Jarvis voice is fully offline. If the chosen
provider isn't installed (e.g. ``piper`` missing), the import fails *at first
use*, not at module import — so the rest of Jarvis (text + dashboard widgets)
still works without the voice deps.
"""
from __future__ import annotations

from dataclasses import dataclass

from shared.config import settings
from shared.voice import get_stt, get_tts


@dataclass
class VoiceTurn:
    transcript: str
    detected_language: str
    reply_text: str
    reply_audio: bytes


class JarvisVoice:
    """Wraps STT + TTS for the Jarvis WS audio path."""

    def __init__(self) -> None:
        self._stt = None  # lazy — don't load Whisper at import time
        self._tts = None

    @property
    def stt(self):
        if self._stt is None:
            self._stt = get_stt(settings.jarvis_stt_provider)
        return self._stt

    @property
    def tts(self):
        if self._tts is None:
            self._tts = get_tts(settings.jarvis_tts_provider)
        return self._tts

    async def transcribe(self, audio: bytes) -> tuple[str, str]:
        t = await self.stt.transcribe(audio)
        return t.text, t.language

    async def synthesize(self, text: str) -> bytes:
        # Jarvis is English-only; force "en" so the offline providers don't
        # try to read a non-English language code from somewhere.
        return await self.tts.synthesize(text, language="en")
