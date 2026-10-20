<div align="center">

# RUHI 🪷
### My personal multilingual AI assistant for Indian languages

Type or speak in **Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi or Odia**, and RUHI replies in the same language, by text or voice.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1C3C3C)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-personal%20project-orange)

</div>

---

## About this project

RUHI started as my own assistant: I wanted to talk to an AI in Telugu and other Indian languages, not just English. It's a **personal, learning-first project**, built with a lot of AI-assisted ("vibe") coding while I learn how speech models, translation, LLMs and agents fit together.

It works on my machine and does what I need. It isn't production-hardened, so expect rough edges.

## How it works

```
┌──────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  User    │ →  │  LID    │ →  │  ASR    │ →  │  NMT    │ →  │ Gemini  │ →  │  TTS    │
│ (text or │    │ Sarvam  │    │ Saarika │    │ Mayura  │    │  2.5    │    │ Bulbul  │
│  voice)  │    │text-lid │    │  v2.5   │    │   v1    │    │  Flash  │    │   v3    │
└──────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                              + LangGraph
                                                                ReAct
```


1. **Detect** the language of each message (Sarvam text-lid)
2. **Transcribe** voice input (Saarika ASR)
3. **Translate** to English (Mayura). English input skips this step
4. **Think**: Gemini 2.5 Flash runs as a LangGraph ReAct agent with tools
5. **Translate back and speak** the reply (Mayura + Bulbul TTS)

Every Sarvam call is cached on disk (SQLite), so repeated phrases cost **0 credits**. That matters on Sarvam's free developer credits.

## Features

- 🗣️ **10 Indian languages** with per-message auto-detection
- 🎙️ **Voice in, voice out**: Saarika ASR + Bulbul TTS (39 voices)
- 🤖 **Agent with 5 tools**: weather, news, web search, calendar, notes
- ⚡ **English fast path** skips both translation legs
- 💾 **Persistent cache**: identical inputs never cost credits twice
- 🧠 **Memory**: ChromaDB long-term plus per-session chat history
- 🔌 **Real-time WebSocket** with HTTP fallback
- 🌙 **Dark glassy UI** in Next.js 14 + Tailwind with Noto Sans Indic fonts

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


### API keys you need

| Key | Where to get it | Used for |
|---|---|---|
| `SARVAM_API_KEY` | [dashboard.sarvam.ai](https://dashboard.sarvam.ai) | language detection, speech, translation, voice |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) | the reasoning model |

Exact variable names are in `config.env.example`. Never commit your `config.env`.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + WebSockets, Python 3.10+ |
| Agent | LangChain 1.x + LangGraph (`create_react_agent`) |
| LLM | Gemini 2.5 Flash (default) · OpenAI · Ollama (selectable) |
| Speech & translation | Sarvam: text-lid · Saarika v2.5 (ASR) · Mayura v1 (NMT) · Bulbul v3 (TTS) |
| Memory | ChromaDB (long-term) + LangChain `InMemoryChatMessageHistory` (per-session) |
| Frontend | Next.js 14 + Tailwind, no Inter font, Noto Sans Indic family |


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


## Testing

```bash
python apps/ruhi_chat/backend/tests/import_smoke.py    # all modules import
python apps/ruhi_chat/backend/tests/smoke_test.py      # full pipeline with fakes (0 credits)
python apps/ruhi_chat/backend/tests/live_minimal.py    # 1 live round-trip (~3 credits, cached after)
```


## Honest status & limitations

- ✅ Text and voice chat in 10 languages, the agent tools and caching all work in my local setup
- ⚠️ Single-user and local only: no auth, no deployment setup
- ⚠️ Depends on paid or credit-based APIs (Sarvam, Gemini). Free tiers run out
- ⚠️ Translation through English can lose nuance in some languages
- ⚠️ Test coverage is basic smoke tests, not a full suite

## What I learned building it

- Chaining speech → translation → LLM → speech, and where latency hides
- Building a ReAct agent with LangGraph and giving it tools
- Caching to make credit-limited APIs affordable
- WebSockets between FastAPI and Next.js

## Roadmap (ideas, no promises)

- [ ] Try open models (e.g. via Ollama) for an offline mode
- [ ] Experiment with fine-tuning or distilling a small model for Telugu
- [ ] Code-mixed input (Telugu + English "Tenglish")
- [ ] Simple Docker setup

## Contributing

It's a personal project, but issues and suggestions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgments

- **[Sarvam AI](https://sarvam.ai)** for the Indian-language speech and translation models
- **[Google Gemini](https://ai.google.dev)** for the reasoning layer
- **[LangChain / LangGraph](https://www.langchain.com/)** for the agent framework
- Built on a rebuilt codebase from an earlier desktop voice assistant

<div align="center">

Made by **[Kundrapu Hemanth](https://www.linkedin.com/in/kundrapu-hemanth)** · still learning, still building

</div>
