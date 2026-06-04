"""RUHI Chat — FastAPI + WebSocket entrypoint.

Endpoints
---------
GET  /                  Health + version + supported languages.
POST /chat/text         Text-in, text-out. ``want_audio=true`` adds TTS.
POST /chat/voice        Multipart audio in, JSON out (transcript, reply, audio).
WS   /chat/ws           Bidirectional stream. Client sends JSON frames; server
                        streams JSON pipeline events back. One session per
                        connection.

Session memory is per-WebSocket: the in-memory chat history lives for the life
of the connection. Long-term semantic memory is parked for a later phase
(``shared.memory.MemoryStore`` is ready when we need it).

Run locally
-----------
    uvicorn apps.ruhi_chat.backend.main:app --host 0.0.0.0 --port 8001
"""
from __future__ import annotations

import base64
import json
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Annotated

logger = logging.getLogger("ruhi.chat")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.chat_history import InMemoryChatMessageHistory
from pydantic import BaseModel

from apps.ruhi_chat.backend.pipeline import ChatPipeline, TurnResult
from shared import __version__
from shared.config import settings
from shared.tools.errors import ToolError


# ── lifecycle ────────────────────────────────────────────────────────


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Eagerly instantiate so the first request doesn't pay setup cost.
    app.state.pipeline = ChatPipeline()
    yield


app = FastAPI(
    title="RUHI Chat",
    version=__version__,
    description="Multilingual Indian-language chatbot (10 languages, Sarvam pipeline).",
    lifespan=_lifespan,
)

# Permissive CORS for the Next.js dev frontend; tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── schemas ──────────────────────────────────────────────────────────


class TextChatRequest(BaseModel):
    text: str
    want_audio: bool = False
    speaker: str | None = None
    hint_language: str | None = None  # ISO 639-1 or BCP-47


class ChatResponse(BaseModel):
    detected_language: str
    user_text_native: str
    user_text_en: str
    reply_en: str
    reply_native: str
    reply_audio_b64: str | None = None
    tool_calls: list[str] = []
    input_mode: str


def _to_response(turn: TurnResult) -> ChatResponse:
    return ChatResponse(
        detected_language=turn.detected_language,
        user_text_native=turn.user_text_native,
        user_text_en=turn.user_text_en,
        reply_en=turn.reply_en,
        reply_native=turn.reply_native,
        reply_audio_b64=(
            base64.b64encode(turn.reply_audio).decode("ascii") if turn.reply_audio else None
        ),
        tool_calls=turn.tool_calls,
        input_mode=turn.input_mode,
    )


# ── HTTP ─────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict:
    return {
        "service": "ruhi-chat",
        "version": __version__,
        "languages": settings.supported_languages,
        "llm_provider": settings.chat_llm_provider,
    }


@app.post("/chat/text", response_model=ChatResponse)
async def chat_text(req: TextChatRequest) -> ChatResponse:
    pipeline: ChatPipeline = app.state.pipeline
    try:
        turn = await pipeline.run(
            text=req.text,
            want_audio=req.want_audio,
            speaker=req.speaker,
            hint_language=req.hint_language,
        )
    except ToolError as e:
        logger.warning("ToolError on /chat/text: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline crashed on /chat/text")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return _to_response(turn)


@app.post("/chat/voice", response_model=ChatResponse)
async def chat_voice(
    audio: Annotated[UploadFile, File(description="WAV/MP3/OGG audio of the user speaking.")],
    want_audio: Annotated[bool, Form()] = True,
    speaker: Annotated[str | None, Form()] = None,
    hint_language: Annotated[str | None, Form()] = None,
) -> ChatResponse:
    pipeline: ChatPipeline = app.state.pipeline
    raw = await audio.read()
    try:
        turn = await pipeline.run(
            audio=raw,
            want_audio=want_audio,
            speaker=speaker,
            hint_language=hint_language,
        )
    except ToolError as e:
        logger.warning("ToolError on /chat/voice: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline crashed on /chat/voice")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return _to_response(turn)


# ── WebSocket ────────────────────────────────────────────────────────


@app.websocket("/chat/ws")
async def chat_ws(ws: WebSocket) -> None:
    await ws.accept()
    pipeline: ChatPipeline = app.state.pipeline
    history = InMemoryChatMessageHistory()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "detail": "Invalid JSON."})
                continue

            kind = msg.get("type")
            want_audio = bool(msg.get("want_audio", False))
            speaker = msg.get("speaker")
            hint = msg.get("hint_language")

            try:
                if kind == "text":
                    logger.info("WS text turn: %r", (msg.get("text") or "")[:80])
                    turn = await pipeline.run(
                        text=msg.get("text", ""),
                        history=history,
                        want_audio=want_audio,
                        speaker=speaker,
                        hint_language=hint,
                    )
                elif kind == "audio":
                    audio_b64 = msg.get("audio_b64", "")
                    audio = base64.b64decode(audio_b64) if audio_b64 else b""
                    logger.info("WS audio turn: %d bytes", len(audio))
                    turn = await pipeline.run(
                        audio=audio,
                        history=history,
                        want_audio=want_audio,
                        speaker=speaker,
                        hint_language=hint,
                    )
                elif kind == "reset":
                    history = InMemoryChatMessageHistory()
                    await ws.send_json({"event": "reset_ok"})
                    continue
                else:
                    await ws.send_json(
                        {"event": "error", "detail": f"Unknown message type: {kind!r}"}
                    )
                    continue
            except ToolError as e:
                logger.warning("ToolError mid-turn: %s", e)
                await ws.send_json({"event": "error", "detail": str(e), "code": e.code})
                continue
            except Exception as e:
                # CRITICAL: any other exception used to drop the WS. Now we
                # surface it as an error frame and keep the connection alive
                # so the user can retry without reloading the page.
                tb = traceback.format_exc()
                logger.error("Unexpected error mid-turn:\n%s", tb)
                await ws.send_json(
                    {
                        "event": "error",
                        "detail": f"{type(e).__name__}: {e}",
                        "code": "internal",
                    }
                )
                continue

            response = _to_response(turn).model_dump()
            response["event"] = "turn"
            await ws.send_json(response)

    except WebSocketDisconnect:
        logger.info("WS disconnected by client")
        return
    except Exception:
        logger.exception("WS handler crashed")
        try:
            await ws.close(code=1011)
        except Exception:
            pass
        return
