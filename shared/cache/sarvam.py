"""SQLite-backed response cache for Sarvam API calls.

Mandatory infrastructure: with only ~1000 dev credits on the Sarvam key, every
repeated test run during development would otherwise burn budget. This cache
keys responses by ``(endpoint, language, sha256(payload))`` so identical calls
cost zero credits on replay.

What gets cached
----------------
- Translation (Mayura) — text in, text out. Cheap and safe to cache.
- TTS (Bulbul) — text in, audio bytes out. Cache by (text, language, voice).
- ASR (Saarika) — audio in, text out. Cache by sha256 of the audio bytes;
  fixture clips replay free.

What does NOT get cached
------------------------
- Streaming responses (token-by-token). Cache full responses only.
- Anything where freshness matters (none in this stack — all calls are
  pure functions of input).

Usage
-----
>>> cache = get_sarvam_cache()
>>> async def call(text, lang):
...     return await cache.get_or_set(
...         endpoint="translate",
...         language=lang,
...         payload={"text": text, "target": "en"},
...         fetch=lambda: real_sarvam_translate(text, lang),
...     )
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Awaitable, Callable

from shared.config import settings


def _hash_payload(payload: Any) -> str:
    """Stable hash of any JSON-serializable payload (or raw bytes)."""
    if isinstance(payload, (bytes, bytearray)):
        return hashlib.sha256(payload).hexdigest()
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SarvamCache:
    """Thread-safe on-disk cache of Sarvam responses."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or settings.sarvam_cache_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sarvam_cache (
                    endpoint   TEXT NOT NULL,
                    language   TEXT NOT NULL,
                    payload_h  TEXT NOT NULL,
                    response   BLOB NOT NULL,
                    is_json    INTEGER NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    PRIMARY KEY (endpoint, language, payload_h)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_created ON sarvam_cache(created_at)"
            )

    # ── public API ────────────────────────────────────────────────────
    def get(self, endpoint: str, language: str, payload: Any) -> Any | None:
        key_h = _hash_payload(payload)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT response, is_json FROM sarvam_cache "
                "WHERE endpoint=? AND language=? AND payload_h=?",
                (endpoint, language, key_h),
            ).fetchone()
        if row is None:
            return None
        blob, is_json = row
        return json.loads(blob.decode("utf-8")) if is_json else blob

    def set(self, endpoint: str, language: str, payload: Any, response: Any) -> None:
        key_h = _hash_payload(payload)
        if isinstance(response, (bytes, bytearray)):
            blob, is_json = bytes(response), 0
        else:
            blob, is_json = json.dumps(response, ensure_ascii=False).encode("utf-8"), 1
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sarvam_cache "
                "(endpoint, language, payload_h, response, is_json) VALUES (?,?,?,?,?)",
                (endpoint, language, key_h, blob, is_json),
            )

    async def get_or_set(
        self,
        *,
        endpoint: str,
        language: str,
        payload: Any,
        fetch: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Return cached response if present, else call ``fetch`` and cache the result.

        Serialized per-process via an asyncio lock so two concurrent identical
        requests don't both burn credits while the first is in flight.
        """
        hit = self.get(endpoint, language, payload)
        if hit is not None:
            return hit
        async with self._lock:
            hit = self.get(endpoint, language, payload)  # double-check
            if hit is not None:
                return hit
            fresh = await fetch()
            self.set(endpoint, language, payload, fresh)
            return fresh

    # ── housekeeping ──────────────────────────────────────────────────
    def stats(self) -> dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT endpoint, COUNT(*) FROM sarvam_cache GROUP BY endpoint"
            ).fetchall()
        return {e: n for e, n in rows}

    def clear(self, endpoint: str | None = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            if endpoint:
                conn.execute("DELETE FROM sarvam_cache WHERE endpoint=?", (endpoint,))
            else:
                conn.execute("DELETE FROM sarvam_cache")


@lru_cache(maxsize=1)
def get_sarvam_cache() -> SarvamCache:
    return SarvamCache()
