"""RUHI Jarvis — FastAPI + WebSocket entrypoint.

Endpoints
---------
GET  /                Health + version + LLM provider + monitor interval.
POST /jarvis/text     One-shot text query, returns final reply + tool list.
WS   /jarvis/ws       Real-time dashboard channel — multiplexes three streams:
                        * agent events (thinking / tool_call / tool_result / reply)
                        * monitor events (CPU/RAM/battery every 2s)
                        * voice events (audio in -> transcript + reply + audio out)

WebSocket protocol
------------------
Client -> server JSON frames:
    {"type": "text", "text": "what is my CPU?"}
    {"type": "audio", "audio_b64": "..."}          # offline ASR -> agent
    {"type": "reset"}                              # clear history

Server -> client JSON frames:
    {"event": "monitor", cpu_percent, memory_percent, ...}     # ~every 2s
    {"event": "thinking", "text": "..."}                       # agent reasoning
    {"event": "tool_call", "name": "...", "args": {...}}
    {"event": "tool_result", "name": "...", "result": "..."}
    {"event": "reply", "text": "..."}
    {"event": "transcript", "text": "...", "language": "en"}   # voice path
    {"event": "audio", "audio_b64": "..."}                     # TTS output
    {"event": "done"}
    {"event": "error", "detail": "..."}

Run locally
-----------
    uvicorn apps.ruhi_jarvis.backend.main:app --host 127.0.0.1 --port 8002
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.chat_history import InMemoryChatMessageHistory
from pydantic import BaseModel

from apps.ruhi_jarvis.backend.agent import JarvisAgent
from apps.ruhi_jarvis.backend.monitors import MonitorHub
from apps.ruhi_jarvis.backend.voice import JarvisVoice
from shared import __version__
from shared.config import settings
from shared.tools.errors import ToolError


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.agent = JarvisAgent()
    app.state.voice = JarvisVoice()  # lazy — doesn't load Whisper/Piper yet
    app.state.monitors = MonitorHub(interval=2.0)
    await app.state.monitors.start()
    try:
        yield
    finally:
        await app.state.monitors.stop()


app = FastAPI(
    title="RUHI Jarvis",
    version=__version__,
    description="Local-first agentic dashboard with offline voice.",
    lifespan=_lifespan,
)

# The dashboard is served separately (React dev or static); allow loopback origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── schemas ──────────────────────────────────────────────────────────


class TextRequest(BaseModel):
    text: str


class TextResponse(BaseModel):
    reply: str
    tool_calls: list[str] = []


# ── HTTP ─────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict:
    return {
        "service": "ruhi-jarvis",
        "version": __version__,
        "llm_provider": settings.jarvis_llm_provider,
        "tts_provider": settings.jarvis_tts_provider,
        "stt_provider": settings.jarvis_stt_provider,
        "monitor_interval_s": app.state.monitors.interval,
    }


@app.post("/jarvis/text", response_model=TextResponse)
async def jarvis_text(req: TextRequest) -> TextResponse:
    agent: JarvisAgent = app.state.agent
    try:
        result = await agent.respond(req.text)
    except ToolError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return TextResponse(**result)


# ── WebSocket ────────────────────────────────────────────────────────


@app.websocket("/jarvis/ws")
async def jarvis_ws(ws: WebSocket) -> None:
    await ws.accept()
    agent: JarvisAgent = app.state.agent
    voice: JarvisVoice = app.state.voice
    monitors: MonitorHub = app.state.monitors
    history = InMemoryChatMessageHistory()

    # Spin up the monitor fan-out for *this* connection.
    monitor_q = monitors.subscribe()

    async def pump_monitors() -> None:
        try:
            while True:
                ev = await monitor_q.get()
                await ws.send_json(ev.to_json())
        except (asyncio.CancelledError, WebSocketDisconnect):
            return

    monitor_task = asyncio.create_task(pump_monitors())

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "detail": "Invalid JSON."})
                continue

            kind = msg.get("type")

            if kind == "reset":
                history = InMemoryChatMessageHistory()
                await ws.send_json({"event": "reset_ok"})
                continue

            if kind == "text":
                user_text = msg.get("text", "")
                await _stream_agent(ws, agent, user_text, history)
                continue

            if kind == "audio":
                audio_b64 = msg.get("audio_b64", "")
                audio = base64.b64decode(audio_b64) if audio_b64 else b""
                try:
                    transcript, lang = await voice.transcribe(audio)
                except Exception as e:
                    await ws.send_json(
                        {"event": "error", "detail": f"STT failed: {e}"}
                    )
                    continue
                await ws.send_json(
                    {"event": "transcript", "text": transcript, "language": lang}
                )
                if not transcript:
                    await ws.send_json({"event": "done"})
                    continue
                final_reply = await _stream_agent(ws, agent, transcript, history)
                if final_reply:
                    try:
                        audio_out = await voice.synthesize(final_reply)
                        await ws.send_json(
                            {
                                "event": "audio",
                                "audio_b64": base64.b64encode(audio_out).decode("ascii"),
                            }
                        )
                    except Exception as e:
                        await ws.send_json(
                            {"event": "error", "detail": f"TTS failed: {e}"}
                        )
                continue

            await ws.send_json(
                {"event": "error", "detail": f"Unknown type: {kind!r}"}
            )
    except WebSocketDisconnect:
        pass
    finally:
        monitor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await monitor_task
        monitors.unsubscribe(monitor_q)


async def _stream_agent(
    ws: WebSocket,
    agent: JarvisAgent,
    user_text: str,
    history: InMemoryChatMessageHistory,
) -> str:
    """Run one agent turn, forwarding every JarvisEvent to the WS. Returns
    the final reply text (or "")."""
    final_reply = ""
    async for ev in agent.stream(user_text, history=history):
        if ev.kind == "reply":
            final_reply = ev.data.get("text", "")
        try:
            await ws.send_json(ev.to_json())
        except WebSocketDisconnect:
            return final_reply
    return final_reply
