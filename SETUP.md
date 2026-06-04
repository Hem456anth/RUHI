# SETUP

Step-by-step installation. Total time on a clean machine: ~10 minutes (most of it is `npm install`).

## 1. Prerequisites

| Tool | Version | Where |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| Git | any recent | https://git-scm.com/ |

Verify:
```bash
python --version    # 3.10+
node --version      # v18+
git --version       # any
```

## 2. Get API keys

Two **required**, the rest are optional (only the agent tools that need them will fail without them).

### Required

| Service | Why | Free tier? | Where |
|---|---|---|---|
| **Sarvam AI** | LID + ASR + NMT + TTS for 10 Indian languages | Yes — 1000 credits | https://dashboard.sarvam.ai/ |
| **Google Gemini** | The reasoning LLM (default: `gemini-2.5-flash`) | Yes — free tier sufficient for dev | https://ai.google.dev/ (AI Studio → Get API key) |

### Optional (per-tool)

| Service | Used by | Where |
|---|---|---|
| OpenWeatherMap | `get_weather` tool | https://openweathermap.org/api |
| NewsAPI | `get_news` tool | https://newsapi.org/ |
| Google Custom Search | `web_search` tool | https://programmablesearchengine.google.com/ (need an API key + CX) |
| Google Calendar OAuth | `upcoming_events` tool | https://console.cloud.google.com/ (OAuth 2.0 client + `credentials.json`) |
| OpenAI | Alternative LLM (`RUHI_CHAT_LLM_PROVIDER=openai`) | https://platform.openai.com/ |

Skip any tool you don't need — the agent gracefully refuses to call tools whose keys aren't set.

## 3. Clone + configure

```bash
git clone https://github.com/Hem456anth/RUHI.git
cd RUHI
cp config.env.example config.env
```

Open `config.env` in any editor and paste your keys:

```ini
# Required
SARVAM_API_KEY=your_sarvam_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional — fill only the tools you want enabled
OPENWEATHER_API_KEY=
NEWS_API_KEY=
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_CX=
```

> **Never commit `config.env`.** It's gitignored, but double-check with `git status` before any commit — you should not see it in the list.

## 4. Backend — Python

```bash
# Create + activate a virtualenv
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install RUHI Chat + its dependencies
pip install -e ".[chat]"
```

What `-e ".[chat]"` does: installs the repo as an editable package (so `import shared, apps` works) and pulls in the optional chat dependencies (Sarvam SDK if available, plus FastAPI, Uvicorn, LangGraph, ChromaDB, etc.).

**Verify the install:**

```bash
python apps/ruhi_chat/backend/tests/import_smoke.py
# Expected: 6/6 import cleanly
```

**Start the backend:**

```bash
uvicorn apps.ruhi_chat.backend.main:app --host 0.0.0.0 --port 8001 --reload
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

Visit <http://localhost:8001/> in a browser — should return JSON listing the 10 languages and your LLM provider.

## 5. Frontend — Next.js

Open a **second** terminal (keep the backend running):

```bash
cd apps/ruhi_chat/frontend
npm install
npm run dev
```

Visit <http://localhost:3000>. The status dot in the top-left of the sidebar (and the top bar) should turn **green** within a second — that means the WebSocket connected to the backend.

If you ever want to point the frontend at a non-default backend address, create `apps/ruhi_chat/frontend/.env.local`:

```ini
NEXT_PUBLIC_RUHI_API=http://your-host:8001
NEXT_PUBLIC_RUHI_WS=ws://your-host:8001
```

## 6. Verify end-to-end with a live call

This burns ~3 Sarvam credits the first time, **0 on replay** because of the cache:

```bash
python apps/ruhi_chat/backend/tests/live_minimal.py
```

Expected output (abridged):

```
sarvam_api_key set: True
gemini_api_key set: True

--- 1. Sarvam LID ---
  detected: en-IN  iso=en

--- 2. Sarvam translate EN -> Telugu ---
  EN: Hello, how are you?
  TE: నమస్కారం, మీరు ఎలా ఉన్నారు?

--- 3. Gemini chat turn ---
  Gemini reply: Hi!

=== LIVE VERIFICATION GREEN ===
```

If you re-run it immediately, every call is a cache hit and **no Sarvam credits are consumed**.

## 7. Common setup issues

### `ModuleNotFoundError: No module named 'shared'`
You're outside the venv, or you forgot `pip install -e ".[chat]"`. Activate the venv and reinstall.

### Frontend status dot stays amber forever
Backend isn't reachable. Check:
1. Backend terminal shows `Uvicorn running on http://0.0.0.0:8001`.
2. Open <http://localhost:8001/> directly — it should return JSON.
3. Browser console — any CORS/WS errors?

### `error parsing value for field "supported_languages"`
You edited the wrong file. Make sure your keys are in `config.env` (no leading dot), not `config.env.example`.

### `gemini-1.5-pro is not found`
Old default; update `shared/llm/factory.py` to use `gemini-2.5-flash` (already in main). If you've forked, pull latest.

### Sarvam `404 Not Found` on `/text/identify-language`
Wrong endpoint. Real path is `/text-lid` (already correct in main; pull latest if forking).

### Mic button shows "permission denied"
Browser-level. Click the 🔒 lock icon in the address bar → Microphone → **Allow**. Browsers only grant mic on `http://localhost` or HTTPS, not on raw LAN IPs.

### `gh: command not found` (Windows)
You installed GitHub CLI but PATH didn't refresh. Close and reopen PowerShell.

## 8. Next steps

- Read **[GUIDE.md](GUIDE.md)** for how to actually use the chat (text + voice + tool calls + multilingual quirks).
- Read **[docs/SPLIT_PLAN.md](docs/SPLIT_PLAN.md)** for the architecture rationale (why Sarvam vs Bhashini, why an English-pivot agent, etc.).
