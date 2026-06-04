# RUHI Chat — Frontend

Next.js 14 + Tailwind. Talks to the FastAPI backend via the `/chat/ws`
WebSocket (with HTTP fallback endpoints also available).

## Run

```bash
cd apps/ruhi_chat/frontend
npm install         # one-time
npm run dev         # http://localhost:3000
```

The backend must be running at `http://localhost:8001` (or override via
`.env.local`). See `../README.md` for the full two-terminal flow.

## Files

```
app/
├── layout.tsx       Global shell, fonts, dark gradient
├── globals.css      Tailwind + .glass utility
└── page.tsx         The chat page (single route)

components/
├── StatusDot.tsx    WS connection indicator
├── MessageBubble.tsx  User / assistant / system bubbles
└── Composer.tsx     Input + 🎙️ recorder + Send

lib/
├── languages.ts     10 Indian languages + script modes
└── useChatSocket.ts WebSocket hook (text + audio + reset)
```

## Things deferred (not blockers)

- **Script toggle** (Latin / Devanagari / Native) is wired into the UI but
  the actual transliteration is left as a follow-up — Sarvam has a separate
  transliterate endpoint we can call client-side or backend-side. For now
  it's a no-op label.
- **Streaming reply tokens.** Backend currently sends the turn as one frame.
  When we move to LangGraph token-streaming on the chat agent we can show
  partial reply text live.
- **Auth / sessions.** Single anonymous WS per browser tab. Production would
  add auth + a persistent session id keyed to the shared `MemoryStore`.
