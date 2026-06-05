"""Typed, single-source-of-truth configuration for RUHI Chat.

Loaded from `config.env` at the repo root. The app imports `settings` from
here; nothing else should read environment variables directly.

Example
-------
>>> from shared.config import settings
>>> settings.sarvam_api_key
>>> settings.supported_languages
['te', 'hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or']
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ENV = REPO_ROOT / "config.env"


class Settings(BaseSettings):
    """RUHI runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=str(CONFIG_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Languages ─────────────────────────────────────────────────────
    # ``NoDecode`` disables pydantic-settings' default JSON parsing of complex
    # fields so our CSV ``a,b,c`` string can be split by the validator below.
    supported_languages: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["te", "hi", "ta", "kn", "ml", "bn", "mr", "gu", "pa", "or"],
        alias="RUHI_SUPPORTED_LANGUAGES",
    )
    default_language: str = Field(default="auto", alias="RUHI_DEFAULT_LANGUAGE")

    # ── Host ──────────────────────────────────────────────────────────
    chat_host: str = Field(default="0.0.0.0", alias="RUHI_CHAT_HOST")
    chat_port: int = Field(default=8001, alias="RUHI_CHAT_PORT")

    # ── LLM ───────────────────────────────────────────────────────────
    chat_llm_provider: Literal["gemini", "openai"] = Field(
        default="gemini", alias="RUHI_CHAT_LLM_PROVIDER"
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # ── Sarvam (primary speech + translation) ─────────────────────────
    sarvam_api_key: str | None = Field(default=None, alias="SARVAM_API_KEY")
    sarvam_cache_path: Path = Field(
        default=REPO_ROOT / ".cache" / "sarvam.sqlite", alias="SARVAM_CACHE_PATH"
    )

    # ── Bhashini (fallback) ───────────────────────────────────────────
    bhashini_user_id: str | None = Field(default=None, alias="BHASHINI_USER_ID")
    bhashini_api_key: str | None = Field(default=None, alias="BHASHINI_API_KEY")
    bhashini_pipeline_id: str | None = Field(default=None, alias="BHASHINI_PIPELINE_ID")

    # ── Memory ────────────────────────────────────────────────────────
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    chroma_persist_dir: Path = Field(
        default=REPO_ROOT / ".cache" / "chroma", alias="CHROMA_PERSIST_DIR"
    )

    # ── Tools (ported) ────────────────────────────────────────────────
    openweather_api_key: str | None = Field(default=None, alias="OPENWEATHER_API_KEY")
    wolfram_app_id: str | None = Field(default=None, alias="WOLFRAM_APP_ID")
    google_credentials_file: Path = Field(
        default=REPO_ROOT / "credentials.json", alias="GOOGLE_CREDENTIALS_FILE"
    )
    google_token_file: Path = Field(
        default=REPO_ROOT / "token.pickle", alias="GOOGLE_TOKEN_FILE"
    )
    google_search_api_key: str | None = Field(default=None, alias="GOOGLE_SEARCH_API_KEY")
    google_search_cx: str | None = Field(default=None, alias="GOOGLE_SEARCH_CX")
    news_api_key: str | None = Field(default=None, alias="NEWS_API_KEY")
    calendar_timezone: str = Field(default="Asia/Kolkata", alias="CALENDAR_TIMEZONE")
    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")

    # ── Legacy voice (optional, kept for tts.py providers — not used by default) ──
    azure_speech_key: str | None = Field(default=None, alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="eastus", alias="AZURE_SPEECH_REGION")
    elevenlabs_key: str | None = Field(default=None, alias="ELEVENLABS_KEY")

    # ── Dev / tracing ─────────────────────────────────────────────────
    enable_tool_trace: bool = Field(default=True, alias="RUHI_ENABLE_TOOL_TRACE")
    enable_live_logs: bool = Field(default=True, alias="RUHI_ENABLE_LIVE_LOGS")

    # ── Validators ────────────────────────────────────────────────────
    @field_validator("supported_languages", mode="before")
    @classmethod
    def _split_languages(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v  # type: ignore[return-value]

    # ── Convenience ──────────────────────────────────────────────────
    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    def require(self, *keys: str) -> None:
        """Raise if any of the listed attributes are unset. Use at app startup."""
        missing = [k for k in keys if not getattr(self, k, None)]
        if missing:
            raise RuntimeError(
                f"Missing required config: {missing}. "
                f"Set them in {CONFIG_ENV} (copy from config.env.example)."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience singleton — import this from anywhere.
settings = get_settings()


if __name__ == "__main__":
    # Sanity check: print non-secret fields when run directly.
    s = get_settings()
    print(f"Supported languages: {s.supported_languages}")
    print(f"Chat LLM provider:   {s.chat_llm_provider}")
    print(f"Sarvam key set:      {bool(s.sarvam_api_key)}")
    print(f"OpenAI key set:      {bool(s.openai_api_key)}")
    print(f"Gemini key set:      {bool(s.gemini_api_key)}")
