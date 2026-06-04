"""LLM provider factory.

A thin wrapper that returns a LangChain-compatible chat model based on the provider
name. Both apps go through this so the agent layer doesn't import vendor SDKs directly.

Providers
---------
- ``gemini``  → ``ChatGoogleGenerativeAI`` (RUHI Chat default — native multilingual)
- ``openai``  → ``ChatOpenAI``
- ``ollama``  → ``ChatOllama`` (RUHI Jarvis default — local-first)

Usage
-----
>>> from shared.llm import get_llm
>>> llm = get_llm("gemini", model="gemini-1.5-pro", temperature=0.2)
"""
from __future__ import annotations

from typing import Any, Literal

from shared.config import settings

Provider = Literal["gemini", "openai", "ollama"]

# Sensible per-provider defaults. Apps can override.
_DEFAULT_MODELS: dict[str, str] = {
    # Gemini 1.5 Pro was retired; 2.5 Pro/Flash are the GA models as of 2026.
    # Flash is fast + cheap and plenty capable for chat — Pro is overkill here.
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "ollama": settings.ollama_model,
}


def get_llm(
    provider: Provider | None = None,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    streaming: bool = True,
    **kwargs: Any,
):
    """Return a configured LangChain chat model.

    Parameters
    ----------
    provider : "gemini" | "openai" | "ollama" | None
        If None, picks the configured default for the current app mode
        (Chat → ``chat_llm_provider``; Jarvis → ``jarvis_llm_provider``).
    model : str, optional
        Override the per-provider default model name.
    temperature, streaming, **kwargs
        Forwarded to the underlying LangChain class.
    """
    if provider is None:
        provider = (
            settings.jarvis_llm_provider
            if settings.app_mode.value == "jarvis"
            else settings.chat_llm_provider
        )

    chosen_model = model or _DEFAULT_MODELS[provider]

    if provider == "gemini":
        settings.require("gemini_api_key")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=chosen_model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            **kwargs,
        )

    if provider == "openai":
        settings.require("openai_api_key")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=chosen_model,
            api_key=settings.openai_api_key,
            temperature=temperature,
            streaming=streaming,
            **kwargs,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=chosen_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            **kwargs,
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")
