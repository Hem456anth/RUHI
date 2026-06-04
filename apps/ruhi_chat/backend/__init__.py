"""RUHI Chat backend — multilingual Indian-language chatbot.

Layers (each in its own module):
- sarvam.py    HTTP client (LID, ASR, NMT, TTS) — all calls cached.
- agent.py     LangChain conversational agent over shared tools.
- pipeline.py  LID → ASR → NMT→EN → agent → NMT→native → TTS orchestrator.
- main.py      FastAPI app + WebSocket.
"""
