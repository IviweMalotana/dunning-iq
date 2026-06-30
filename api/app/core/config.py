"""Application configuration, read from the environment.

Local development defaults to a SQLite file so the app is fully clickable with
zero setup (`make seed && make dev`). Production (Railway) sets ``DATABASE_URL``
to the managed Postgres instance. The SQLAlchemy models use portable column
types so the same migrations run against either backend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env (one level up from /api) and /api/.env are both honoured.
_API_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_API_DIR.parent / ".env", _API_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Dunning IQ"
    environment: str = "development"
    debug: bool = True

    # --- Database ---
    # Default: local SQLite file at /api/dunning_iq.db. Override with a Postgres
    # URL in production, e.g. postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = f"sqlite:///{_API_DIR / 'dunning_iq.db'}"

    # --- CORS ---
    # Comma-separated list of allowed origins for the Next.js frontend.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- LLM provider ---
    # The decision engine routes through this provider when its key is set;
    # otherwise it falls back to the deterministic billing playbook.
    llm_provider: str = "claude"          # "claude" | "kimi"
    agent_max_tokens: int = 1024

    # Kimi (Moonshot AI) — OpenAI-compatible API.
    moonshot_api_key: str | None = None
    kimi_model: str = "kimi-k2-0711-preview"
    kimi_base_url: str = "https://api.moonshot.ai/v1"

    # Anthropic Claude — default provider. Haiku 4.5 is the cheapest current
    # Claude model ($1/$5 per MTok) and supports structured output via
    # messages.parse — well-suited to a portfolio demo with predictable cost.
    anthropic_api_key: str | None = None
    claude_model: str = "claude-haiku-4-5"

    # --- Webhooks ---
    # Optional shared secret for verifying inbound payment webhooks.
    webhook_signing_secret: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        """Accept Railway/Heroku-style ``postgres[ql]://`` and upgrade to psycopg3.

        SQLAlchemy 2 requires an explicit driver. Most managed Postgres providers
        hand out URLs without one (``postgresql://...``), which raises
        ``NoSuchModuleError: postgres`` at engine creation. Normalising here means
        you can paste the provider's URL verbatim into the env var.
        """
        if not v or v.startswith("sqlite"):
            return v
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def active_llm_key(self) -> str | None:
        """The API key for the selected provider, or None if not configured."""
        if self.llm_provider == "kimi":
            return self.moonshot_api_key
        if self.llm_provider == "claude":
            return self.anthropic_api_key
        return None

    @property
    def active_llm_model(self) -> str:
        return self.kimi_model if self.llm_provider == "kimi" else self.claude_model

    @property
    def agent_live_enabled(self) -> bool:
        """True when the selected provider has a key and the live engine should run."""
        return bool(self.active_llm_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
