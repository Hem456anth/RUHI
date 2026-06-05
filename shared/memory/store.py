"""ChromaDB-backed memory for RUHI Chat.

Two layers:

1. ``MemoryStore`` — long-term semantic memory in ChromaDB. Collections are
   namespaced ``<app>__<session_id>`` so different surfaces (chat, future
   variants) can coexist without bleeding into each other.
2. ``conversation_memory()`` — a per-session ``InMemoryChatMessageHistory``
   (LangChain 1.x) for short-term turn-by-turn context the agent consumes directly.

Usage
-----
>>> from shared.memory import get_memory_store
>>> store = get_memory_store()
>>> store.add("chat", "session-42", "User asked about weather in Hyderabad")
>>> store.search("chat", "session-42", "weather", k=3)
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.chat_history import InMemoryChatMessageHistory

from shared.config import settings

AppName = Literal["chat"]


def _collection_name(app: AppName, session_id: str) -> str:
    # Chroma collection names must be 3–63 chars, alnum/_/-.
    safe = session_id.replace("/", "_").replace(" ", "_")
    return f"{app}__{safe}"[:63]


@dataclass
class MemoryHit:
    text: str
    metadata: dict
    distance: float


class MemoryStore:
    """Persistent semantic memory wrapper around ChromaDB."""

    def __init__(self, persist_dir: str | None = None) -> None:
        persist = persist_dir or str(settings.chroma_persist_dir)
        self._client = chromadb.PersistentClient(
            path=persist,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )

    # ── writes ────────────────────────────────────────────────────────
    def add(
        self,
        app: AppName,
        session_id: str,
        text: str,
        *,
        metadata: dict | None = None,
        id: str | None = None,
    ) -> str:
        coll = self._client.get_or_create_collection(_collection_name(app, session_id))
        doc_id = id or f"{session_id}-{coll.count() + 1}"
        coll.add(ids=[doc_id], documents=[text], metadatas=[metadata or {}])
        return doc_id

    # ── reads ─────────────────────────────────────────────────────────
    def search(
        self,
        app: AppName,
        session_id: str,
        query: str,
        *,
        k: int = 5,
    ) -> list[MemoryHit]:
        coll = self._client.get_or_create_collection(_collection_name(app, session_id))
        if coll.count() == 0:
            return []
        result = coll.query(query_texts=[query], n_results=min(k, coll.count()))
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        return [
            MemoryHit(text=d, metadata=m or {}, distance=float(dist))
            for d, m, dist in zip(docs, metas, dists)
        ]

    def clear(self, app: AppName, session_id: str) -> None:
        try:
            self._client.delete_collection(_collection_name(app, session_id))
        except Exception:
            # Collection didn't exist — nothing to do.
            pass


@lru_cache(maxsize=1)
def get_memory_store() -> MemoryStore:
    return MemoryStore()


# ── short-term conversational memory ──────────────────────────────────
def conversation_memory() -> InMemoryChatMessageHistory:
    """Fresh per-session chat-message history for an agent turn loop.

    LangChain 1.x replaced ``ConversationBufferMemory`` with the
    ``BaseChatMessageHistory`` interface — pass this into
    ``RunnableWithMessageHistory`` (LangChain) or wire it into a LangGraph
    state directly.

    For cross-session recall, use ``MemoryStore.search`` to retrieve relevant
    prior turns and prepend them to the system prompt or this history.
    """
    return InMemoryChatMessageHistory()
