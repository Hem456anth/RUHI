"""Pluggable text-to-speech.

Strategy: ``TTSProvider`` is the only interface the agent layer sees.
Concrete providers are imported lazily so that, e.g., RUHI Chat doesn't pull
in Piper, and RUHI Jarvis doesn't pull in the Sarvam SDK.

Providers
---------
- ``MockTTS``         — zero-dep, returns empty bytes. Use for unit tests
                        and credit-free dev runs.
- ``SarvamTTS``       — Bulbul, Indian-language voices, cached.   [RUHI Chat]
- ``PiperTTS``        — offline, lightweight, English.            [RUHI Jarvis]
- ``VibeVoiceTTS``    — offline, premium quality, English, GPU.   [RUHI Jarvis opt-in]
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from shared.config import settings


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

    The actual HTTP call lives in ``apps/ruhi-chat/backend/sarvam.py`` to keep
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


class PiperTTS(TTSProvider):
    """Offline TTS via Piper. Default for RUHI Jarvis."""

    name = "piper"
    output_format = "wav"

    def __init__(self, voice: str | None = None):
        self.voice = voice or settings.piper_voice
        self._synth = None  # lazy

    def _ensure_loaded(self):
        if self._synth is None:
            from piper import PiperVoice  # type: ignore[import-not-found]

            self._synth = PiperVoice.load(self.voice)

    async def synthesize(self, text: str, *, language: str = "en", voice: str | None = None) -> bytes:
        import io
        import wave

        self._ensure_loaded()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            self._synth.synthesize(text, wav)
        return buf.getvalue()


class VibeVoiceTTS(TTSProvider):
    """Premium offline TTS via Microsoft VibeVoice-1.5B. Opt-in (needs GPU)."""

    name = "vibevoice"
    output_format = "wav"

    def __init__(self):
        self._pipeline = None

    def _ensure_loaded(self):
        if self._pipeline is None:
            # Import deferred so users without the model installed don't pay
            # the load cost.
            from vibevoice import VibeVoicePipeline  # type: ignore[import-not-found]

            self._pipeline = VibeVoicePipeline.from_pretrained("microsoft/VibeVoice-1.5B")

    async def synthesize(self, text: str, *, language: str = "en", voice: str | None = None) -> bytes:
        self._ensure_loaded()
        return self._pipeline.synthesize(text)  # implementation TBD when integrated


# ── factory ──────────────────────────────────────────────────────────


def get_tts(provider: str | None = None, **kwargs) -> TTSProvider:
    """Return the configured TTS provider.

    If ``provider`` is None, picks based on app mode:
    - chat → ``MockTTS`` (Chat uses ``SarvamTTS`` constructed inside the
      Chat backend with the live Sarvam client; we keep the shared default
      mock-safe so importing this module never burns credits).
    - jarvis → ``settings.jarvis_tts_provider``.
    """
    if provider is None:
        provider = (
            settings.jarvis_tts_provider
            if settings.app_mode.value == "jarvis"
            else "mock"
        )

    if provider == "mock":
        return MockTTS()
    if provider == "piper":
        return PiperTTS(**kwargs)
    if provider == "vibevoice":
        return VibeVoiceTTS()
    if provider == "sarvam":
        # Caller must inject the bulbul client.
        return SarvamTTS(**kwargs)
    raise ValueError(f"Unknown TTS provider: {provider!r}")
