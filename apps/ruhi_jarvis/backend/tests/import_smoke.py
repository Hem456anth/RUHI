"""Cheapest verification: every Jarvis backend module imports cleanly."""
from __future__ import annotations

import importlib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

MODULES = [
    "apps.ruhi_jarvis",
    "apps.ruhi_jarvis.backend",
    "apps.ruhi_jarvis.backend.tools",
    "apps.ruhi_jarvis.backend.agent",
    "apps.ruhi_jarvis.backend.monitors",
    "apps.ruhi_jarvis.backend.voice",
    "apps.ruhi_jarvis.backend.main",
]


def main() -> int:
    failed = 0
    for m in MODULES:
        try:
            importlib.import_module(m)
            print(f"  OK  {m}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {m}  -> {type(e).__name__}: {e}")
    print()
    print(f"{len(MODULES) - failed}/{len(MODULES)} import cleanly")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
