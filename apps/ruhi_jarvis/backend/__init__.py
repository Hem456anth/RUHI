"""RUHI Jarvis backend — local-first agentic dashboard.

Layers:
- tools.py     Jarvis tool set (system control + info + web + notes).
- agent.py     LangGraph ReAct agent over Ollama, with thought streaming.
- monitors.py  Periodic system-stats push loop for dashboard widgets.
- voice.py     Offline STT (Whisper) + TTS (Piper / VibeVoice).
- main.py      FastAPI app + WebSocket that multiplexes agent + monitors + voice.
"""
