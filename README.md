# RUHI Chat

**Multilingual AI chatbot for 10 Indian languages.** Type or speak in Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, or Odia — RUHI replies in the same language.

```
┌──────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  User    │ →  │  LID    │ →  │  ASR    │ →  │  NMT    │ →  │ Gemini  │ →  │  TTS    │
│ (text or │    │ Sarvam  │    │ Saarika │    │ Mayura  │    │  2.5    │    │ Bulbul  │
│  voice)  │    │text-lid │    │  v2.5   │    │   v1    │    │  Flash  │    │   v3    │
└──────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                              + LangGraph
                                                                ReAct
```

Every Sarvam call is cached on disk — repeated phrases cost **0 credits** on replay. With Sarvam's 1000-credit dev allotment, that's the difference between a weekend prototype and a real product.

## Quick start

```bash
# 1. Clone
git clone https://github.com/Hem456anth/RUHI.git && cd RUHI

# 2. Backend
python -m venv .venv && .venv/Scripts/activate    # Windows; use .venv/bin/activate on macOS/Linux
pip install -e ".[chat]"
cp config.env.example config.env                  # then add your Sarvam + Gemini keys
uvicorn apps.ruhi_chat.backend.main:app --port 8001

# 3. Frontend (new terminal)
cd apps/ruhi_chat/frontend
npm install
npm run dev                                       # http://localhost:3000
```

See **[SETUP.md](SETUP.md)** for the full install + API-key guide and **[GUIDE.md](GUIDE.md)** for how to use the chat once it's running.

## Features

- **10 Indian languages** with per-message auto-detection (Sarvam LID).
- **Voice in + voice out** — Saarika ASR for speech, Bulbul TTS for responses (39 voices).
- **Agent layer** — LangGraph ReAct with 5 tools: weather, news, web search, calendar, notes.
- **English-direct fast path** — typing in English skips both translation legs (saves credits).
- **Persistent SQLite cache** — identical inputs cost zero Sarvam credits forever.
- **Real-time WebSocket** with HTTP fallback endpoints.
- **Dark glassy UI** — Next.js 14 + Tailwind, ten Noto Sans Indic scripts loaded.

## Project layout

```
RUHI/
├── shared/                     # core: config, LLM factory, ChromaDB memory, cache, tools, voice
├── apps/ruhi_chat/
│   ├── backend/                # FastAPI + WS + Sarvam client + LangGraph agent + pipeline
│   └── frontend/               # Next.js 14 + Tailwind
├── README.md                   # this file
├── SETUP.md                    # detailed install + API keys
├── GUIDE.md                    # usage + troubleshooting
├── pyproject.toml              # Python deps (root)
└── config.env.example          # env template (copy to config.env)
```

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + WebSockets, Python 3.10+ |
| Agent | LangChain 1.x + LangGraph (`create_react_agent`) |
| LLM | Gemini 2.5 Flash (default) · OpenAI · Ollama (selectable) |
| Speech & translation | Sarvam: text-lid · Saarika v2.5 (ASR) · Mayura v1 (NMT) · Bulbul v3 (TTS) |
| Memory | ChromaDB (long-term) + LangChain `InMemoryChatMessageHistory` (per-session) |
| Frontend | Next.js 14 + Tailwind, no Inter font, Noto Sans Indic family |

## Testing

```bash
python apps/ruhi_chat/backend/tests/import_smoke.py    # all modules import
python apps/ruhi_chat/backend/tests/smoke_test.py      # full pipeline with fakes (0 credits)
python apps/ruhi_chat/backend/tests/live_minimal.py    # 1 live round-trip (~3 credits, cached after)
```

## License

MIT.

## Acknowledgments

- **[Sarvam AI](https://sarvam.ai)** — Indian-language speech + translation models.
- **[Google Gemini](https://ai.google.dev)** — reasoning layer.
- Built on the codebase rebuild of an earlier desktop voice assistant.
