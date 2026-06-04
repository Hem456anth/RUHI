# RUHI Split — Build Plan

Breaking the single PyQt5 desktop assistant into **two web products sharing one core**:

1. **RUHI Chat** — multilingual AI chatbot for 10 Indian languages (cloud, Bhashini pipeline)
2. **RUHI Jarvis** — local-first agentic JARVIS dashboard (offline voice, LangGraph, live widgets)

Strategy chosen: **mono-repo, shared core first, reuse existing feature code where clean.**

---

## 1. Where you are vs. where you're going

| | Now | Target |
|---|---|---|
| Shape | One PyQt5 desktop app (`main.py`) | Two web apps + shared core |
| UI | PyQt5 `.ui` + GIFs | Next.js (Chat) / React+Tailwind (Jarvis) |
| Backend | In-process functions | FastAPI + WebSocket (one per product) |
| Brains | if/else command matching | LangChain agent (Chat) / LangGraph ReAct (Jarvis) |
| Voice | Snap-detect + gTTS/Azure/ElevenLabs | Bhashini ASR/TTS (Chat) · Whisper+Piper offline (Jarvis) |
| Memory | `conversation_history.json` | ChromaDB + LangChain ConvMemory |

This is **not** a refactor of `main.py` — it's a new architecture that *ports the good feature functions* out of the old code.

---

## 2. Target mono-repo layout

```
RUHI/
├── docker-compose.yml          # chat-api, jarvis-api, chromadb, ollama
├── config.env                  # shared API keys (gitignored)
├── pyproject.toml              # shared Python deps
│
├── shared/                     # ← THE SHARED CORE (build this first)
│   ├── config.py               # pydantic Settings: app mode, languages, hosts, keys
│   ├── llm/
│   │   └── factory.py          # get_llm(provider) → Gemini | GPT-4o | Ollama
│   ├── memory/
│   │   └── store.py            # ChromaDB client + LangChain ConvMemory wrapper
│   ├── voice/
│   │   ├── tts.py              # ported TTSManager (+ Bhashini/Sarvam, Piper)
│   │   └── stt.py              # Whisper + Bhashini ASR
│   └── tools/                  # ported feature functions, framework-agnostic
│       ├── weather.py          # ← Ruhi/features/weather.py
│       ├── system_stats.py     # ← Ruhi/features/system_stats.py
│       ├── system_control.py   # ← features/automation/system_control.py
│       ├── data_retriever.py   # ← features/internet/data_retriever.py
│       ├── calendar.py         # ← Ruhi/features/google_calendar.py
│       ├── news.py · email.py · search.py · app_launch.py · notes.py · location.py
│
└── apps/
    ├── ruhi-chat/
    │   ├── backend/
    │   │   ├── main.py         # FastAPI + WebSocket
    │   │   ├── sarvam.py       # Sarvam client: LID, ASR (Saarika), NMT, TTS (Bulbul) — PRIMARY
    │   │   ├── bhashini.py     # Bhashini client — fallback (when key acquired)
    │   │   ├── pipeline.py     # LID → ASR → NMT→EN → agent → NMT→native → TTS
    │   │   └── agent.py        # LangChain conversational agent
    │   └── frontend/           # Next.js: chat UI, language switcher, script toggle
    │
    └── ruhi-jarvis/
        ├── backend/
        │   ├── main.py         # FastAPI + WebSocket (real-time stream)
        │   ├── agent.py        # LangGraph ReAct: plan → act → observe, streamed
        │   ├── tools.py        # wires shared/tools: web search, file ops, app launch
        │   └── monitors.py     # CPU/RAM/disk push loop → dashboard widgets
        └── frontend/           # React + Tailwind dark JARVIS dashboard (local only)
```

---

## 3. Reuse map — what survives the split

### ✅ Port directly (clean, self-contained) → `shared/tools/`
| Old file | Becomes | Used by |
|---|---|---|
| `Ruhi/features/weather.py` `fetch_weather()` | `tools/weather.py` | Both (Chat answers, Jarvis widget) |
| `Ruhi/features/system_stats.py` `system_stats()` | `tools/system_stats.py` | Jarvis CPU/RAM widget |
| `features/automation/system_control.py` `SystemControl` | `tools/system_control.py` | Jarvis (brightness/volume/wifi/launch/close) |
| `features/internet/data_retriever.py` `DataRetriever` | `tools/data_retriever.py` | Both (news/weather/stocks/search) — *scraping stubs need real impl* |
| `Ruhi/features/google_calendar.py` | `tools/calendar.py` | Both |
| `news.py · note.py · send_email.py · google_search.py · launch_app.py · loc.py` | matching `tools/*` | Jarvis mostly |

### ♻️ Port + extend → `shared/voice/`
| `features/voice/tts_manager.py` `TTSManager` | `voice/tts.py` | Add **Bhashini/Sarvam** (Chat) and **Piper offline** (Jarvis) providers alongside existing gTTS/Azure/ElevenLabs |

### 📖 Reference only — do not port
- `main.py`, `main_fixed.py` — PyQt5 monolith + snap detection (logic is reference for wake-word)
- `Ruhi/features/gui.py`, `gui.ui`, `Ruhi/utils/images/*` — replaced by web frontends
- `features/reasoning/query_classifier.py`, `features/generation/ai_generator.py` — **empty stubs**; LangChain/LangGraph replaces their intended role

---

## 4. Build order

### Phase 0 — Scaffolding & hygiene
- [ ] Create `apps/`, `shared/`, `docs/` skeleton; move nothing destructively yet
- [ ] **Security: `Jarvis/config/config.py` is tracked in git.** `git rm --cached` it, confirm `config.env` is gitignored, and **rotate any leaked keys** (OpenAI, Azure, Weather, ElevenLabs, Google)
- [ ] `pyproject.toml` + `config.env.example`

### Phase 1 — Shared core (both products depend on this)
- [ ] `shared/config.py` — pydantic Settings (languages list, app mode, hosts, keys)
- [ ] `shared/llm/factory.py` — provider switch (Gemini / GPT-4o / Ollama)
- [ ] `shared/memory/store.py` — ChromaDB + ConvMemory
- [ ] Port the ✅ tools above into `shared/tools/` as plain `async` callables (decouple from `Ruhi.config`)
- [ ] `shared/voice/tts.py` + `stt.py`

### Phase 2 — Backends (parallel, both thin over shared core)
**2A · Chat** — `sarvam.py` client behind a `SpeechProvider` + `TranslationProvider` interface → `pipeline.py` (LID→ASR→NMT→agent→NMT→TTS) → LangChain agent → FastAPI WS. **Sarvam is primary** (key in hand, **1000 credits — treat as dev budget**): Saarika ASR, Mayura NMT, Bulbul TTS — one vendor for the whole Indian-language stack. Bhashini slot reserved as a fallback provider for when its key arrives.

> **Credit conservation rules** (so 1000 credits last through Phase 2A + 3A):
> - Every Sarvam call goes through a **response cache** (`shared/cache/sarvam.py`, keyed by `(endpoint, lang, hash(payload))`, on-disk SQLite). Re-running the same test phrase = zero credits.
> - **Text mode first.** Build & test the agent + translation path with typed input long before turning on voice. ASR/TTS are the expensive legs.
> - Keep a small **fixture set** of canonical test phrases (one per language) — voice E2E runs only hit those, never random new audio.
> - Use **Bulbul short-form** for dev, long-form only for demos.
> - Mock provider stays available behind the interface for offline pipeline-shape testing.
**2B · Jarvis** — LangGraph ReAct agent with thought-streaming → `tools.py` (shared tools: web search, file ops, app launch) → `monitors.py` system push → FastAPI WS. **Voice fully offline** (Whisper base.en + Piper, optionally VibeVoice-1.5B if GPU available), no cloud fallback.

### Phase 3 — Frontends (parallel)
**3A · Chat** — Next.js chat UI, language switcher, Devanagari↔Latin↔native script toggle
**3B · Jarvis** — React+Tailwind dark dashboard: CPU/RAM ring, clock, weather, calendar, ETF feed, news, **agent thought stream**, voice log

### Phase 4 — Integration
- [ ] `docker-compose.yml`: chat-api, jarvis-api, chromadb, ollama
- [ ] Shared `config.env` wiring
- [ ] Chat: deploy target (hosted web app). Jarvis: local Docker only.
- [ ] End-to-end smoke test per product

---

## 5. Key decisions (rationale)

1. **Mono-repo with `shared/`** — your requirement is "shared core"; one repo keeps tool code DRY across both products. Two separate deployables via `apps/`.
2. **Voice stacks diverge by product** — Chat is cloud-multilingual (**Sarvam primary, Bhashini fallback**, 10 languages); Jarvis is **fully offline** (**Whisper base.en + Piper**, optional VibeVoice-1.5B, no cloud fallback). Don't force one stack on both.
3. **LLM split** — Chat: Gemini 1.5 Pro / GPT-4o (native multilingual). Jarvis: Ollama (Mistral 7B) local + Gemini fallback (matches your existing Docker setup).
4. **Different agent frameworks on purpose** — Chat needs lightweight conversational memory (LangChain). Jarvis needs visible plan→act→observe with tool routing and a live thought log (LangGraph ReAct).
5. **Drop the empty stubs** — `query_classifier`/`ai_generator` were never implemented; the agent layer is their replacement.

---

## 6. Decisions locked
- **Chat speech/translation:** **Sarvam AI is primary** (key acquired, **1000 credits left** — see credit conservation rules in §Phase 2A). Saarika ASR + Mayura NMT + Bulbul TTS — covers all 10 target Indian languages from one vendor. Bhashini reserved as a secondary provider behind the same interface for when its key is acquired.
- **Jarvis voice:** fully offline — Whisper base.en + Piper + Ollama. Optional VibeVoice-1.5B provider for premium voice if GPU is available. No cloud fallback.
- **n8n:** out of scope. It was only an example in the mockups; not part of this project. Jarvis tools = web search, file ops, app launch.
- **Deploy:** RUHI Chat = hosted web app. RUHI Jarvis = local Docker only.
