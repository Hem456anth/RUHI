"""Web search tool.

Replaces the placeholder scrapers in legacy ``features/internet/data_retriever.py``
with a real implementation via Google Custom Search (JSON API). Falls back to
ToolError if no API key is configured rather than returning ``"N/A"`` dicts
like the old code did.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from shared.config import settings
from shared.tools.errors import ToolError

_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


async def web_search(query: str, *, limit: int = 5) -> list[SearchResult]:
    settings.require("google_search_api_key", "google_search_cx")
    params = {
        "key": settings.google_search_api_key,
        "cx": settings.google_search_cx,
        "q": query,
        "num": min(limit, 10),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GOOGLE_CSE_URL, params=params)
    if resp.status_code != 200:
        raise ToolError(f"Google CSE returned {resp.status_code}", code="upstream")
    data = resp.json()
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
        )
        for item in data.get("items", [])[:limit]
    ]
