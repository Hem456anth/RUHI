# GUIDE

How to actually use RUHI Chat once you've followed [SETUP.md](SETUP.md).

## 1. The chat in 10 seconds

Open <http://localhost:3000>:

- **Left sidebar:** brand, language switcher, pipeline info, status dot.
- **Main:** message list, composer at the bottom.
- **Composer:** text input + mic + Send. Below: voice-output toggle, kbd hints.

Type anything in any of the 10 supported languages, hit `Enter`. RUHI detects the language, calls Gemini, and replies in the same script.

## 2. Languages

| ISO | Native | English | Status |
|---|---|---|---|
| `te` | తెలుగు | Telugu | ✓ |
| `hi` | हिन्दी | Hindi | ✓ |
| `ta` | தமிழ் | Tamil | ✓ |
| `kn` | ಕನ್ನಡ | Kannada | ✓ |
| `ml` | മലയാളം | Malayalam | ✓ |
| `bn` | বাংলা | Bengali | ✓ |
| `mr` | मराठी | Marathi | ✓ |
| `gu` | ગુજરાતી | Gujarati | ✓ |
| `pa` | ਪੰਜਾਬੀ | Punjabi | ✓ |
| `or` | ଓଡ଼ିଆ | Odia | ✓ |
| `en` | English | English | ✓ (fast path) |

**Language switcher** in the sidebar:
- **Auto** (default) — Sarvam LID detects per message. Costs 1 LID call per turn.
- A specific language — skips LID entirely. Saves 1 call per turn if you know what language you'll always be typing.

## 3. The pipeline (what happens behind the scenes)

For a Telugu input like `నాకు హైదరాబాద్ వాతావరణం చెప్పు`:

```
1. LID         "te-IN" detected      (~1 credit, cached)
2. NMT to EN   → "Tell me weather of Hyderabad"   (~1 credit, cached)
3. Agent       LangGraph ReAct picks get_weather, returns "Sunny, 32°C"
               (Gemini tokens billed by Google)
4. NMT to TE   → "హైదరాబాద్‌లో ఇప్పుడు ఎండగా ఉంది, 32°C."   (~1 credit, cached)
5. TTS         (only if "Voice reply" toggle is on)   (~1-3 credits, cached)
6. Render      bubble + tool-call chips + audio player
```

**English input** skips steps 2 and 4 entirely (LID short-circuits to `en-IN`), so an English question costs ~0 Sarvam credits beyond the LID.

## 4. Voice in (microphone)

1. Click the 🎙️ mic button → browser prompts for mic permission → click **Allow**.
2. Speak. The button pulses red while recording, with a `recording · Ns` indicator.
3. Click ■ to stop.
4. Audio uploads → Saarika ASR → rest of pipeline → reply.

**Tip:** speak in any of the 10 languages. ASR auto-detects, and the pipeline routes through Sarvam.

If the mic icon doesn't trigger a permission prompt:
- Make sure you're on `http://localhost:3000` (browsers block `getUserMedia` on raw LAN IPs over HTTP).
- Check OS-level mic permission: **Settings → Privacy → Microphone**.

## 5. Voice out (Bulbul TTS)

The **"Voice reply"** checkbox at the bottom of the composer.

- **Off (default):** text only. Free (after Sarvam LID/NMT).
- **On:** every reply is also synthesized as a WAV with Bulbul, ~1–3 credits per reply (proportional to character count). Cached — replaying the same reply costs nothing.

Default voice is `shubh` (Bulbul v3). 39 voices available; the WebSocket protocol accepts a `speaker` field but the UI currently doesn't expose it. Hit the backend directly to override:

```bash
curl -X POST http://localhost:8001/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते","want_audio":true,"speaker":"priya"}'
```

## 6. Tool calls

The agent has 5 tools. When it uses one, you'll see chips above the reply:

```
USED  get_weather
┌─────────────────────────────────┐
│ The weather in Hyderabad is …   │
└─────────────────────────────────┘
```

| Tool | Triggers when… | Requires key |
|---|---|---|
| `get_weather` | "weather in X" | `OPENWEATHER_API_KEY` |
| `get_news` | "news", "headlines", "today's news" | `NEWS_API_KEY` |
| `web_search` | "search X", "look up X", "what is X" (when knowledge cutoff matters) | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_CX` |
| `upcoming_events` | "my calendar", "what's on today" | OAuth `credentials.json` |
| `make_note` | "save a note", "remember this" | — |

If a tool's key is missing, the agent will either decline gracefully or surface a `ToolError` in the chat as a red dashed line. Set the key in `config.env` and restart the backend.

## 7. Cache behavior — why repeated phrases are free

Every Sarvam call is wrapped by `shared/cache/sarvam.py`:

```
key = (endpoint, language, sha256(payload))
```

Identical inputs hit the on-disk SQLite (`.cache/sarvam.sqlite` by default) and skip the network entirely.

**What's cached:**
- LID — by text content
- NMT — by `(source, target, text)`
- TTS — by `(text, language, speaker)`
- ASR — by sha256 of the audio bytes

**Inspect the cache:**

```python
from shared.cache import get_sarvam_cache
print(get_sarvam_cache().stats())
# {'lid': 12, 'translate': 28, 'tts': 4, 'asr': 6}
```

**Clear the cache:**

```python
get_sarvam_cache().clear()                  # everything
get_sarvam_cache().clear(endpoint="tts")    # just TTS
```

## 8. WebSocket protocol (for custom clients)

The frontend uses this; you can talk to the backend the same way:

**Connect:** `ws://localhost:8001/chat/ws`

**Client → server frames:**

```jsonc
// Text
{"type": "text", "text": "Hello", "want_audio": false, "hint_language": "en"}

// Voice (base64 audio)
{"type": "audio", "audio_b64": "...", "want_audio": true}

// Clear session memory
{"type": "reset"}
```

**Server → client frames:**

```jsonc
// Successful turn
{"event":"turn","detected_language":"te-IN","user_text_native":"...",
 "user_text_en":"...","reply_en":"...","reply_native":"...",
 "reply_audio_b64":null,"tool_calls":["get_weather"],"input_mode":"text"}

// Error during a turn — connection stays open
{"event":"error","detail":"<message>","code":"sarvam_429"}

// Reset acknowledgment
{"event":"reset_ok"}
```

The HTTP REST equivalents are `POST /chat/text` and `POST /chat/voice` (multipart upload).

## 9. Reset, history, sessions

- **Reset button** (top of the chat) clears in-memory history for the active WebSocket connection.
- **History scope:** one in-memory `InMemoryChatMessageHistory` per WS connection. Open a second browser tab → fresh session.
- **Persistent memory** (`shared/memory/store.py`, ChromaDB-backed) exists but isn't wired into the WS handler yet. It's there for future "remember across sessions" features.

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Status dot amber forever | WebSocket reconnect loop in the React hook (old build) | Pull latest; the hook stabilizes `onError` in a ref. |
| Message sent, no reply, WS drops | Backend crashed mid-turn | Backend prints traceback in its terminal. The most common cause is a tool whose key is missing. Surface as red bubble now, not WS-drop. |
| `404 Not Found` from Sarvam LID | Stale endpoint path | The real path is `/text-lid`, not `/text/identify-language`. Pull latest. |
| Gemini `404 NOT_FOUND model gemini-1.5-pro` | Retired model | Default is now `gemini-2.5-flash`. Update `shared/llm/factory.py` or set a different `RUHI_CHAT_LLM_PROVIDER`. |
| Telugu/Hindi/etc. shows as boxes (□□□) | Missing Indic font | The frontend loads Noto Sans Indic fonts from Google Fonts at runtime. Allow `fonts.googleapis.com` and `fonts.gstatic.com` if you're behind a strict proxy. |
| TTS audio plays as silence | `MockTTS` is active (no Sarvam key) | Set `SARVAM_API_KEY` in `config.env` and restart. |
| Sarvam returns `429 Too Many Requests` | You've burned through dev credits | Top up via the Sarvam dashboard, or set `SARVAM_CACHE_PATH` to a fresh cache file and run smoke tests with mock providers. |

## 11. Common requests, by phrasing

The agent responds equally well to any of the 10 supported languages. Examples (try in the UI):

| Language | Prompt |
|---|---|
| English | `What's the weather in Hyderabad?` |
| Telugu  | `నాకు హైదరాబాద్ వాతావరణం చెప్పు` |
| Hindi   | `आज की मुख्य खबरें क्या हैं?` |
| Tamil   | `சென்னையில் என்ன நிகழ்வுகள் உள்ளன?` |
| Kannada | `ಬೆಂಗಳೂರಿನ ಹವಾಮಾನ ಹೇಗಿದೆ?` |
| Bengali | `আজকের প্রধান সংবাদ কী?` |

Use the **suggestion chips** on the empty-state screen — they're pre-filled multilingual prompts.

## 12. Where to file bugs

[github.com/Hem456anth/RUHI/issues](https://github.com/Hem456anth/RUHI/issues)

Include:
- Backend traceback (from the uvicorn terminal)
- Browser console errors (F12)
- The exact prompt you sent
- The cache stats: `python -c "from shared.cache import get_sarvam_cache; print(get_sarvam_cache().stats())"`
