# RUHI Chat

Multilingual AI chatbot for 10 Indian languages. End-to-end: a Sarvam-powered
speech + translation pipeline behind a LangChain agent, served via FastAPI WS,
fronted by a Next.js dark glassy UI.

```
apps/ruhi_chat/
├── backend/    FastAPI + WebSocket — Sarvam pipeline + Gemini agent
└── frontend/   Next.js 14 + Tailwind — chat UI, language switcher, voice button
```

---

## Quick start

You need **two terminals**.

### 1. Backend (Python 3.10+, repo root .venv)

```bash
# from repo root
cp config.env.example config.env           # then fill SARVAM_API_KEY + GEMINI_API_KEY
.venv/Scripts/python -m pip install -e .   # one-time
uvicorn apps.ruhi_chat.backend.main:app --host 0.0.0.0 --port 8001
```

Visit <http://localhost:8001/> — should return JSON listing languages & provider.

### 2. Frontend (Node 18+)

```bash
cd apps/ruhi_chat/frontend
npm install
cp .env.local.example .env.local           # only if backend is not on localhost:8001
npm run dev
```

Then open <http://localhost:3000> in a browser. The status dot in the top-right
turns green when the WebSocket connects to the backend.

---

## Try it

| Input | What happens |
|---|---|
| Type English: `Hello, how are you?` | Both translate legs skip → Gemini replies → reply shown verbatim. Cheapest path. |
| Type Telugu: `నాకు హైదరాబాద్ వాతావరణం చెప్పు` | LID → translate to EN → agent calls `get_weather` → translate reply back to Telugu. |
| Toggle **Voice output** on, send any message | Reply rendered as both text **and** audio (Bulbul TTS — costs credits). |
| Click 🎙️, speak, click ■ | Audio → Saarika ASR → LID → pipeline as above. |

Every Sarvam call is cached on disk (`.cache/sarvam.sqlite`). The same phrase
on a second run costs **0 credits**.

---

## Endpoints

| Endpoint | Use |
|---|---|
| `GET  /` | Health, version, supported languages, LLM provider |
| `POST /chat/text` | One-shot: `{"text": "...", "want_audio": false}` → `ChatResponse` |
| `POST /chat/voice` | Multipart audio upload → `ChatResponse` |
| `WS   /chat/ws` | Streaming session. Frames: `{type: "text"\|"audio"\|"reset", ...}`. |

WebSocket frames (server → client):

```jsonc
// turn complete
{"event": "turn", "detected_language": "te-IN", "user_text_native": "...",
 "user_text_en": "...", "reply_en": "...", "reply_native": "...",
 "reply_audio_b64": null, "tool_calls": ["get_weather"], "input_mode": "text"}

// errors
{"event": "error", "detail": "...", "code": "sarvam_429"}

// after reset request
{"event": "reset_ok"}
```

---

## Configuration

All keys live in `config.env` at the repo root (gitignored). Frontend reads
two `NEXT_PUBLIC_*` vars from `.env.local` for the API/WS URL.

| Required | Used for |
|---|---|
| `SARVAM_API_KEY` | ASR, LID, NMT, TTS |
| `GEMINI_API_KEY` | Agent LLM (or use `OPENAI_API_KEY` and `RUHI_CHAT_LLM_PROVIDER=openai`) |

Optional (only if you use the corresponding tools):
`OPENWEATHER_API_KEY`, `NEWS_API_KEY`, `GOOGLE_SEARCH_API_KEY`+`GOOGLE_SEARCH_CX`,
plus `credentials.json` for Google Calendar.

---

## Tests

```bash
# 21/21 shared imports + 6/6 backend imports
.venv/Scripts/python apps/ruhi_chat/backend/tests/import_smoke.py

# Full pipeline shape with fake Sarvam (zero credits)
.venv/Scripts/python apps/ruhi_chat/backend/tests/smoke_test.py

# Live minimum-credit check (~3 credits first run, 0 on replay)
.venv/Scripts/python apps/ruhi_chat/backend/tests/live_minimal.py
```

---

## Credit budget

Sarvam dev key starts at 1000 credits. Rough costs per leg:

| Leg | ~Cost | Notes |
|---|---|---|
| LID  | ~1 | Per text input |
| NMT  | ~1 | Per direction (skipped for English input) |
| ASR  | varies by clip length | Cached by sha256 of bytes |
| TTS  | varies by chars | Cached by `(text, lang, voice)` |

The cache is mandatory — see `shared/cache/sarvam.py`. Inspect with:

```python
from shared.cache import get_sarvam_cache
print(get_sarvam_cache().stats())
```
