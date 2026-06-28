"""Application configuration, read from the environment.

Local development defaults to a SQLite file so the app is fully clickable with
zero setup (`make seed && make dev`). Production (Railway) sets ``DATABASE_URL``
to the managed Postgres instance. The SQLAlchemy models use portable column
types so the same migrations run against either backend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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

    # --- Anthropic / agent ---
    anthropic_api_key: str | None = None
    # Latest, most capable models. Opus for high-stakes reasoning by default.
    agent_model: str = "claude-opus-4-8"
    agent_max_tokens: int = 1024

    # --- Webhooks ---
    # Optional shared secret for verifying inbound payment webhooks.
    webhook_signing_secret: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def agent_live_enabled(self) -> bool:
        """True when a real key is present and the live engine should run."""
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
