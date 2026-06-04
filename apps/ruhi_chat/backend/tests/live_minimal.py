"""Minimum-credit live test against the real Sarvam + Gemini keys.

What it does (cost in real credits/tokens):
  1. Verify Settings actually loaded the keys (0 credits)
  2. One Sarvam LID call on a tiny string  (~1 Sarvam credit, cached after)
  3. One Sarvam translate EN -> Telugu      (~1 Sarvam credit, cached after)
  4. One Gemini chat turn (no agent tools)  (~negligible tokens, cached by Google)

Total first run:  ~2 Sarvam credits + a sliver of Gemini.
Reruns:            0 credits (cache hits).
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))


async def main() -> int:
    from shared.config import settings

    print(f"--- Config check (0 credits) ---")
    print(f"  sarvam_api_key set: {bool(settings.sarvam_api_key)}")
    print(f"  gemini_api_key set: {bool(settings.gemini_api_key)}")
    print(f"  chat_llm_provider : {settings.chat_llm_provider}")
    if not settings.sarvam_api_key or not settings.gemini_api_key:
        print("FAIL: missing keys in config.env")
        return 1

    from apps.ruhi_chat.backend.sarvam import SarvamClient
    from shared.cache import get_sarvam_cache

    cache = get_sarvam_cache()
    pre_stats = cache.stats()
    print(f"\n--- Cache state before run ---")
    print(f"  {pre_stats or 'empty'}")

    sarvam = SarvamClient()

    print(f"\n--- 1. Sarvam LID (real call, ~1 credit if cold) ---")
    lid = await sarvam.identify_language("hello, how are you")
    print(f"  detected: {lid.language_code}  iso={lid.iso_code}")

    print(f"\n--- 2. Sarvam translate EN -> Telugu (real call, ~1 credit if cold) ---")
    translated = await sarvam.translate(
        "Hello, how are you?", source="en", target="te"
    )
    print(f"  EN: Hello, how are you?")
    print(f"  TE: {translated.text}  (source={translated.detected_source})")

    print(f"\n--- 3. Gemini chat turn (single call) ---")
    from shared.llm import get_llm

    llm = get_llm("gemini")
    from langchain_core.messages import HumanMessage

    resp = await llm.ainvoke([HumanMessage("Say hi in one short sentence.")])
    print(f"  Gemini reply: {resp.content}")

    post_stats = cache.stats()
    print(f"\n--- Cache state after run ---")
    print(f"  {post_stats}")
    new_entries = sum(post_stats.values()) - sum(pre_stats.values())
    print(f"  new cached entries this run: {new_entries}")
    print(f"  (replay of this exact script = 0 Sarvam credits)")

    print(f"\n=== LIVE VERIFICATION GREEN ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
