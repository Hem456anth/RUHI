# RUHI Jarvis

**Local-first agentic dashboard.** English-only voice + chat assistant that runs entirely on your machine — Ollama for reasoning, Whisper for ASR, Piper (or VibeVoice) for TTS. The sibling of [RUHI Chat](../ruhi_chat/) (multilingual cloud chatbot); both share the same `shared/` core.

```
┌─────────────────────────┐
│  React Dashboard (TBD)  │
└────────────┬────────────┘
             │ WebSocket — multiplexed:
             │   • agent thought stream (thinking / tool_call / tool_result / reply)
             │   • monitor pushes  (CPU / RAM / disk / battery, every 2s)
             │   • voice in / out  (audio_b64)
┌────────────▼────────────┐
│  FastAPI                │
│   ├─ JarvisAgent        │  LangGraph ReAct over Ollama (Mistral 7B / Gemma)
│   │   └─ 12 tools       │  system_stats, set_brightness, set_volume,
│   │                     │  launch_app, close_app, get_weather, get_news,
│   │                     │  web_search, upcoming_events, make_note, …
│   ├─ MonitorHub         │  fan-out: 1 producer loop, N WS subscribers
│   └─ JarvisVoice        │  Whisper STT + Piper TTS (lazy-loaded)
└─────────────────────────┘
```

## What's here, what's not

**Here (this PR):** the full backend — agent + tools + monitors + voice + FastAPI WebSocket, plus 5 smoke tests (no Ollama required) and 1 live-Ollama probe.

**Not here yet:** the React dashboard frontend. The WebSocket protocol is fully defined in `main.py` so the frontend can be built against a real backend whenever it's prioritized.

## Quick start

```bash
# 1. Install Jarvis-specific deps (one-time, on top of the shared core)
pip install -e ".[jarvis]"

# 2. Install + run Ollama, pull a tool-capable model
#    https://ollama.com/download
ollama pull llama3.2          # or gemma3, mistral:7b, etc.
ollama serve                  # in another terminal if not running as a service

# 3. Tell Jarvis which model to use (in config.env at the repo root)
#    RUHI_JARVIS_LLM_PROVIDER=ollama
#    OLLAMA_MODEL=llama3.2
#    JARVIS_STT_PROVIDER=whisper
#    JARVIS_TTS_PROVIDER=piper

# 4. Run
uvicorn apps.ruhi_jarvis.backend.main:app --host 127.0.0.1 --port 8002
```

Visit <http://127.0.0.1:8002/> → JSON health probe with the active providers.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Health + LLM/STT/TTS provider info + monitor interval |
| `POST /jarvis/text` | One-shot text → final reply (no streaming) |
| `WS /jarvis/ws` | Real-time dashboard channel — see protocol below |

## WebSocket protocol

**Client → server frames:**

```jsonc
{"type": "text", "text": "What's my CPU at?"}
{"type": "audio", "audio_b64": "..."}    // mic capture, base64-encoded
{"type": "reset"}                        // clear conversation history
```

**Server → client frames** (multiplexed — agent + monitor + voice all on one socket):

```jsonc
// Agent reasoning (streamed step-by-step as LangGraph progresses)
{"event": "thinking",     "text": "I should check the live stats."}
{"event": "tool_call",    "name": "system_stats", "args": {}}
{"event": "tool_result",  "name": "system_stats", "result": "CPU 12%, RAM 47%."}
{"event": "reply",        "text": "Your system looks healthy."}
{"event": "done"}

// Monitor push — every 2s, regardless of agent activity
{"event": "monitor", "cpu_percent": 12.3, "memory_percent": 47.8, "battery_percent": 88, ...}

// Voice path
{"event": "transcript", "text": "...", "language": "en"}
{"event": "audio", "audio_b64": "..."}    // TTS output

// Errors (don't kill the WS — surface and continue)
{"event": "error", "detail": "..."}
```

## Tool set (12 tools)

| Tool | Use | Key required? |
|---|---|---|
| `system_stats`, `system_info` | live CPU/RAM/disk/battery | — |
| `set_brightness`, `set_volume`, `set_wifi` | system control | — (some need admin) |
| `launch_app`, `close_app` | application control with aliases | — |
| `get_weather` | weather by city | `OPENWEATHER_API_KEY` |
| `get_news` | top headlines | `NEWS_API_KEY` |
| `web_search` | Google Custom Search | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_CX` |
| `upcoming_events` | Google Calendar | OAuth `credentials.json` |
| `make_note` | quick text notes | — |

Tools whose keys are missing simply aren't called by the agent (`ToolError` if invoked anyway, surfaced as an error event, WS stays alive).

## Tests

```bash
# Plumbing — no Ollama, no Whisper, no Piper
python apps/ruhi_jarvis/backend/tests/import_smoke.py    # 7/7 modules
python apps/ruhi_jarvis/backend/tests/smoke_test.py      # agent stream shape, monitor fan-out, slow consumer, voice providers

# Live — requires Ollama running with at least one model pulled
python apps/ruhi_jarvis/backend/tests/live_ollama.py     # adapts to whatever model you have
```

## Voice providers

`shared.voice.get_stt` and `shared.voice.get_tts` are pluggable interfaces. Jarvis defaults to **fully offline**:

| Layer | Default | Alternative |
|---|---|---|
| STT | `whisper` (faster-whisper base.en) | — (offline only by spec) |
| TTS | `piper` (en_US-lessac-medium) | `vibevoice` (Microsoft VibeVoice-1.5B — premium quality, needs GPU, opt-in via `JARVIS_TTS_PROVIDER=vibevoice`) |

No cloud fallback. If a provider package isn't installed, the lazy import fails at first use (not at module import), so the rest of Jarvis still works.

## Design notes

- **Per-process singletons** — one `JarvisAgent`, one `MonitorHub`, one `JarvisVoice`, created in the FastAPI lifespan. Per-WS history is held by the WS handler.
- **Monitor fan-out** — one producer loop, async queue per subscriber, oldest-drop on overflow so a slow client can't stall the producer.
- **Thought streaming** — `agent.stream()` yields structured `JarvisEvent` per LangGraph step (per-step, not per-token; robust across LangGraph versions).
- **`_extract_text` shared with Chat** — both agents normalize `AIMessage.content` (which can be a list of typed blocks under LangChain 1.x + Gemini) to a plain string. Without this, replies surface as Python repr strings (the bug PR #2 caught for Chat).

## Differences from RUHI Chat

| | Chat | Jarvis |
|---|---|---|
| Languages | 10 Indian + English | English only |
| LLM | Gemini 2.5 Flash | Ollama (local) |
| Voice | Sarvam Saarika + Bulbul (cloud) | Whisper + Piper (offline) |
| Translation | Mayura, end-to-end | none — monolingual |
| Tools | 5 (chat-focused) | 12 (system + info + tools) |
| Memory | per-WS in-memory | per-WS in-memory (ChromaDB scaffold present, not wired) |
| Deploy | hosted web app | local Docker / local process only |
