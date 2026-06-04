"""Sarvam AI HTTP client — language ID, ASR (Saarika), translate (Mayura), TTS (Bulbul).

Every call routes through ``shared.cache.sarvam`` so identical inputs cost
zero credits on replay. With only 1000 dev credits this is the line between
"plenty for the whole product" and "burned in an afternoon."

API reference (June 2026)
-------------------------
- Base URL:        https://api.sarvam.ai
- Auth header:     ``api-subscription-key: <key>`` (lowercase, hyphenated)
- Language codes:  BCP-47 with ``-IN`` suffix (``te-IN``, ``hi-IN``, ``en-IN``…)
- LID endpoint:    POST ``/text-lid``                body ``{"input": ...}``
- ASR endpoint:    POST ``/speech-to-text``          multipart: file + form fields
- Translate:       POST ``/translate``               body uses ``input`` + ``*_language_code``
- TTS:             POST ``/text-to-speech``          returns base64 WAV in JSON

The shared layer (``shared.voice.SarvamSTT`` / ``SarvamTTS``) takes callables
that match the signatures below; we wire them in ``pipeline.py``.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Literal

import httpx

from shared.cache import get_sarvam_cache
from shared.config import settings
from shared.tools.errors import ToolError
from shared.voice.stt import Transcript

# ── constants ────────────────────────────────────────────────────────

BASE_URL = "https://api.sarvam.ai"

# ISO 639-1 (settings) → BCP-47 (Sarvam) for the 10 target languages + English.
ISO_TO_BCP47: dict[str, str] = {
    "te": "te-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "pa": "pa-IN",
    "or": "od-IN",  # Sarvam uses "od" for Odia
    "en": "en-IN",
    "auto": "auto",
}


def to_bcp47(code: str) -> str:
    """Best-effort normalization to Sarvam's BCP-47 codes."""
    if "-" in code:  # already BCP-47
        return code
    return ISO_TO_BCP47.get(code.lower(), code)


# ── result types ─────────────────────────────────────────────────────


@dataclass
class LanguageId:
    language_code: str       # BCP-47, e.g. "te-IN"
    script_code: str | None  # e.g. "Telu"
    iso_code: str            # short ISO, e.g. "te"

    @classmethod
    def from_sarvam(cls, body: dict) -> "LanguageId":
        bcp = body.get("language_code") or "und"
        return cls(
            language_code=bcp,
            script_code=body.get("script_code"),
            iso_code=bcp.split("-")[0],
        )


# ── client ───────────────────────────────────────────────────────────


class SarvamClient:
    """Thin async wrapper around the Sarvam REST API.

    One client per process; safe to share across requests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
        tts_model: str = "bulbul:v3",
        tts_default_speaker: str = "shubh",
        translate_model: str = "mayura:v1",
        asr_model: str = "saarika:v2.5",
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.timeout = timeout
        self.tts_model = tts_model
        self.tts_default_speaker = tts_default_speaker
        self.translate_model = translate_model
        self.asr_model = asr_model
        self._cache = get_sarvam_cache()

    def _headers(self, *, json_body: bool = True) -> dict[str, str]:
        if not self.api_key:
            raise ToolError(
                "SARVAM_API_KEY is not set. Add it to config.env.",
                code="auth",
            )
        h = {"api-subscription-key": self.api_key}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    # ── 1. Language identification ───────────────────────────────────
    async def identify_language(self, text: str) -> LanguageId:
        payload = {"input": text}
        body = await self._cache.get_or_set(
            endpoint="lid",
            language="auto",
            payload=payload,
            fetch=lambda: self._post_json("/text-lid", payload),
        )
        return LanguageId.from_sarvam(body)

    # ── 2. Translation (Mayura) ──────────────────────────────────────
    async def translate(
        self,
        text: str,
        *,
        source: str,
        target: str,
        mode: Literal["formal", "modern-colloquial", "classic-colloquial"] = "formal",
    ) -> str:
        src_bcp = to_bcp47(source)
        tgt_bcp = to_bcp47(target)
        payload = {
            "input": text,
            "source_language_code": src_bcp,
            "target_language_code": tgt_bcp,
            "mode": mode,
            "model": self.translate_model,
            "enable_preprocessing": False,
        }
        body = await self._cache.get_or_set(
            endpoint="translate",
            language=f"{src_bcp}->{tgt_bcp}",
            payload=payload,
            fetch=lambda: self._post_json("/translate", payload),
        )
        return body.get("translated_text", "")

    # ── 3. Speech to text (Saarika) ──────────────────────────────────
    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str | None = None,
        filename: str = "audio.wav",
    ) -> Transcript:
        # Multipart file payload, hashed by audio bytes for free replays.
        cache_key = {
            "audio_sha": "bytes",  # actual hash is the payload itself below
            "language": language or "auto",
            "model": self.asr_model,
        }
        cached = self._cache.get("asr", language or "auto", audio)
        if cached is not None:
            if isinstance(cached, dict):
                return Transcript(**cached)
            return cached  # legacy raw

        body = await self._call_asr(audio, filename=filename, language=language)
        transcript = Transcript(
            text=body.get("transcript", "").strip(),
            language=body.get("language_code", language or "auto"),
            confidence=float(body.get("confidence", 0.0)) if body.get("confidence") else 0.0,
        )
        self._cache.set("asr", language or "auto", audio, transcript.__dict__)
        return transcript

    async def _call_asr(self, audio: bytes, *, filename: str, language: str | None) -> dict:
        headers = self._headers(json_body=False)  # multipart
        files = {"file": (filename, audio, "audio/wav")}
        data: dict[str, str] = {"model": self.asr_model}
        if language and language != "auto":
            data["language_code"] = to_bcp47(language)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{BASE_URL}/speech-to-text", headers=headers, files=files, data=data
            )
        self._raise_for_status(resp, "asr")
        return resp.json()

    # ── 4. Text to speech (Bulbul) ───────────────────────────────────
    async def synthesize(
        self,
        text: str,
        *,
        language: str,
        speaker: str | None = None,
        pace: float = 1.0,
    ) -> bytes:
        """Return WAV bytes. Long inputs are chunked at 2500-char boundaries."""
        tgt = to_bcp47(language)
        chosen_speaker = speaker or self.tts_default_speaker

        # Sarvam caps at 2500 chars per request.
        chunks = _split_for_tts(text, max_chars=2500)
        out = bytearray()
        for chunk in chunks:
            payload = {
                "text": chunk,
                "target_language_code": tgt,
                "speaker": chosen_speaker,
                "pace": pace,
                "model": self.tts_model,
            }
            body = await self._cache.get_or_set(
                endpoint="tts",
                language=tgt,
                payload=payload,
                fetch=lambda p=payload: self._post_json("/text-to-speech", p),
            )
            audios = body.get("audios", [])
            for b64 in audios:
                out.extend(base64.b64decode(b64))
        return bytes(out)

    # ── internals ────────────────────────────────────────────────────
    async def _post_json(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{BASE_URL}{path}", headers=self._headers(), json=payload
            )
        self._raise_for_status(resp, path.strip("/"))
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: httpx.Response, what: str) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise ToolError(
                f"Sarvam {what} failed ({resp.status_code}): {detail}",
                code=f"sarvam_{resp.status_code}",
            )


# ── helpers ──────────────────────────────────────────────────────────


def _split_for_tts(text: str, *, max_chars: int) -> list[str]:
    """Split text into <= max_chars chunks at sentence boundaries when possible."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        # Try to split at the last sentence-ending punctuation before the cap.
        cut = max(
            remaining.rfind(". ", 0, max_chars),
            remaining.rfind("। ", 0, max_chars),  # Devanagari full stop + space
            remaining.rfind("? ", 0, max_chars),
            remaining.rfind("! ", 0, max_chars),
        )
        if cut == -1:
            cut = remaining.rfind(" ", 0, max_chars)
        if cut == -1:
            cut = max_chars
        chunks.append(remaining[: cut + 1].strip())
        remaining = remaining[cut + 1 :].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks
