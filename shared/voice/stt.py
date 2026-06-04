"""Pluggable speech-to-text.

Mirrors ``shared.voice.tts``. Implementations are lazy-imported so neither app
pays for the other's stack.

Providers
---------
- ``MockSTT``         — returns "" for any audio. Tests and credit-free dev.
- ``SarvamSTT``       — Saarika ASR, Indian languages, cached.   [RUHI Chat]
- ``WhisperSTT``      — faster-whisper, offline.                 [RUHI Jarvis]
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.config import settings


@dataclass
class Transcript:
    text: str
    language: str
    confidence: float = 0.0


class STTProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcript:
        ...


# ── implementations ──────────────────────────────────────────────────


class MockSTT(STTProvider):
    name = "mock"

    async def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcript:
        return Transcript(text="", language=language or "en", confidence=0.0)


class SarvamSTT(STTProvider):
    """Saarika ASR via Sarvam. Cached by sha256 of the audio bytes — fixture
    clips replay free.
    """

    name = "sarvam"

    def __init__(self, call_saarika):
        # call_saarika: async (audio_bytes, language|None) -> Transcript
        self._call_saarika = call_saarika

    async def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcript:
        from shared.cache import get_sarvam_cache

        cache = get_sarvam_cache()
        payload = audio  # hashed directly
        cached = await cache.get_or_set(
            endpoint="asr",
            language=language or "auto",
            payload=payload,
            fetch=lambda: self._call_saarika(audio, language),
        )
        if isinstance(cached, Transcript):
            return cached
        # Cache returned the JSON dict form; reconstruct.
        return Transcript(**cached)


class WhisperSTT(STTProvider):
    """Offline ASR via faster-whisper. Default for RUHI Jarvis."""

    name = "whisper"

    def __init__(self, model: str | None = None):
        self.model_name = model or settings.whisper_model
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            self._model = WhisperModel(self.model_name, compute_type="int8")

    async def transcribe(self, audio: bytes, *, language: str | None = None) -> Transcript:
        import io

        self._ensure_loaded()
        segments, info = self._model.transcribe(
            io.BytesIO(audio), language=language, beam_size=1
        )
        text = " ".join(seg.text for seg in segments).strip()
        return Transcript(text=text, language=info.language, confidence=info.language_probability)


# ── factory ──────────────────────────────────────────────────────────


def get_stt(provider: str | None = None, **kwargs) -> STTProvider:
    if provider is None:
        provider = (
            settings.jarvis_stt_provider
            if settings.app_mode.value == "jarvis"
            else "mock"
        )

    if provider == "mock":
        return MockSTT()
    if provider == "whisper":
        return WhisperSTT(**kwargs)
    if provider == "sarvam":
        return SarvamSTT(**kwargs)
    raise ValueError(f"Unknown STT provider: {provider!r}")
