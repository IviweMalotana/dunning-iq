"""Dunning IQ FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=f"{settings.app_name} API",
    description="AI agent that handles failed recurring payments end to end.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    """Liveness probe with a hint about the agent's operating mode."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "sqlite" if settings.is_sqlite else "postgres",
        "agent_mode": "live" if settings.agent_live_enabled else "replay",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.active_llm_model,
    }


# Routers are mounted as milestones land.
from app.api import cases, dashboard, meta, policy, webhooks  # noqa: E402

app.include_router(meta.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(policy.router)
