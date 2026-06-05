"""Pluggable text-to-speech.

Strategy: ``TTSProvider`` is the only interface the agent layer sees.
Concrete providers are imported lazily so that, e.g., the shared layer
doesn't pull in vendor SDKs at import time.

Providers
---------
- ``MockTTS``   — zero-dep, returns silent WAV. Use for unit tests
                  and credit-free dev runs.
- ``SarvamTTS`` — Bulbul, Indian-language voices, cached.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal


class TTSProvider(ABC):
    """Async TTS interface. Implementations return audio bytes (wav or mp3)."""

    name: str = "abstract"
    output_format: Literal["wav", "mp3"] = "wav"

    @abstractmethod
    async def synthesize(self, text: str, *, language: str = "en", voice: str | None = None) -> bytes:
        ...


# ── implementations ──────────────────────────────────────────────────


class MockTTS(TTSProvider):
    """No-op TTS for tests and credit-free dev. Returns a 44-byte WAV header."""

    name = "mock"
    _SILENT_WAV = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80\xbb\x00\x00\x00\xee\x02\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    async def synthesize(self, text: str, *, language: str = "en", voice: str | None = None) -> bytes:
        return self._SILENT_WAV


class SarvamTTS(TTSProvider):
    """Bulbul TTS via Sarvam. Cached aggressively because of the credit budget.

    The actual HTTP call lives in ``apps/ruhi_chat/backend/sarvam.py`` to keep
    the shared layer SDK-agnostic; this class delegates via dependency
    injection so the shared layer stays import-light.
    """

    name = "sarvam"
    output_format = "wav"

    def __init__(self, call_bulbul):
        # call_bulbul: async (text, language, voice) -> bytes
        self._call_bulbul = call_bulbul

    async def synthesize(self, text: str, *, language: str = "en", voice: str | None = None) -> bytes:
        from shared.cache import get_sarvam_cache

        cache = get_sarvam_cache()
        payload = {"text": text, "voice": voice or "default", "language": language}
        return await cache.get_or_set(
            endpoint="tts",
            language=language,
            payload=payload,
            fetch=lambda: self._call_bulbul(text, language, voice),
        )


# ── factory ──────────────────────────────────────────────────────────


def get_tts(provider: str | None = None, **kwargs) -> TTSProvider:
    """Return a TTS provider by name.

    Defaults to ``MockTTS`` — the Chat backend wires up ``SarvamTTS`` with
    its live Bulbul client so importing this module never burns credits.
    """
    if provider is None:
        provider = "mock"

    if provider == "mock":
        return MockTTS()
    if provider == "sarvam":
        # Caller must inject the bulbul client.
        return SarvamTTS(**kwargs)
    raise ValueError(f"Unknown TTS provider: {provider!r}")
