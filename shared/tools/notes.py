"""Quick note tool — saves text to a timestamped file.

Ported from ``Ruhi/features/note.py``: dropped the hard-coded Notepad++ path
(out of scope for headless backends). Returns the file path so the agent can
echo it back.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from shared.config import settings


NOTES_DIR = settings.repo_root / ".cache" / "notes"


async def make_note(text: str, *, name_hint: str | None = None) -> Path:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    suffix = f"-{name_hint}" if name_hint else ""
    path = NOTES_DIR / f"{ts}{suffix}.txt"
    path.write_text(text, encoding="utf-8")
    return path
