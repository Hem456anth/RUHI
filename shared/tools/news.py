"""News tool — NewsAPI top headlines.

Replaces the hardcoded API key in legacy ``Ruhi/features/news.py`` with the
shared settings.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from shared.config import settings
from shared.tools.errors import ToolError

_BASE_URL = "https://newsapi.org/v2/top-headlines"


@dataclass
class Article:
    title: str
    url: str
    source: str
    description: str = ""


async def get_news(
    *,
    sources: str | None = None,
    country: str | None = "in",
    query: str | None = None,
    limit: int = 10,
) -> list[Article]:
    settings.require("news_api_key")
    params: dict[str, str | int] = {"apiKey": settings.news_api_key, "pageSize": limit}
    if sources:
        params["sources"] = sources
    elif country:
        params["country"] = country
    if query:
        params["q"] = query

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_BASE_URL, params=params)
    if resp.status_code != 200:
        raise ToolError(f"NewsAPI returned {resp.status_code}", code="upstream")
    data = resp.json()
    return [
        Article(
            title=a.get("title", ""),
            url=a.get("url", ""),
            source=(a.get("source") or {}).get("name", ""),
            description=a.get("description", "") or "",
        )
        for a in data.get("articles", [])
    ]
