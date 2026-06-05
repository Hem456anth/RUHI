"""Optional live test against a local Ollama daemon.

Skips gracefully if Ollama isn't running or the configured model isn't
pulled. The Jarvis backend still works without it — you can swap the LLM
provider to gemini/openai by setting ``RUHI_JARVIS_LLM_PROVIDER`` in
``config.env``. This script just proves the local-first happy path.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))


async def main() -> int:
    import httpx
    from shared.config import settings

    print(f"--- Ollama probe ({settings.ollama_base_url}) ---")
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            resp = await c.get(f"{settings.ollama_base_url}/api/tags")
        if resp.status_code != 200:
            print(f"  Ollama responded {resp.status_code}; skipping live test.")
            return 0
        installed = [m["name"] for m in resp.json().get("models", [])]
        print(f"  Installed models: {installed or '(none)'}")
        if not installed:
            print("  No models pulled. Run: ollama pull llama3.2  (or any tool-calling model)")
            return 0
        configured_base = settings.ollama_model.split(":")[0]
        chosen = next(
            (m for m in installed if m.startswith(configured_base)),
            installed[0],
        )
        if chosen != settings.ollama_model:
            print(
                f"  Configured {settings.ollama_model!r} not present; "
                f"using available model {chosen!r} for this probe."
            )
    except Exception as e:
        print(f"  Ollama not running ({type(e).__name__}: {e}); skipping.")
        print(
            f"  To enable: install Ollama, run `ollama serve`, "
            f"then `ollama pull {settings.ollama_model}`."
        )
        return 0

    print(f"\n--- Live agent turn through Ollama ({chosen}) ---")
    from apps.ruhi_jarvis.backend.agent import JarvisAgent
    from shared.llm import get_llm

    agent = JarvisAgent(llm=get_llm("ollama", model=chosen))
    async for ev in agent.stream("What's my current CPU usage?"):
        print(f"  [{ev.kind}] {ev.data}")
    print("\n=== LIVE OLLAMA GREEN ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
