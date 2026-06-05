"""Pluggable speech-to-text.

Mirrors ``shared.voice.tts``. Implementations are lazy-imported so the shared
layer never pays for a vendor SDK at import time.

Providers
---------
- ``MockSTT``   — returns "" for any audio. Tests and credit-free dev.
- ``SarvamSTT`` — Saarika ASR, Indian languages, cached.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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


# ── factory ──────────────────────────────────────────────────────────


def get_stt(provider: str | None = None, **kwargs) -> STTProvider:
    """Return an STT provider by name. Defaults to ``MockSTT``."""
    if provider is None:
        provider = "mock"

    if provider == "mock":
        return MockSTT()
    if provider == "sarvam":
        return SarvamSTT(**kwargs)
    raise ValueError(f"Unknown STT provider: {provider!r}")
