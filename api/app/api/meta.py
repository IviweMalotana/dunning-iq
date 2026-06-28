"""Meta endpoints: version, agent mode, and other non-domain info."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": __version__, "app": settings.app_name}
