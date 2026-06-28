"""Inbound payment webhook endpoint (Stripe/Paddle-shaped)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_signature
from app.db.session import get_db
from app.schemas.webhooks import IngestResult, PaymentWebhookEvent
from app.services.ingest import process_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payments", response_model=IngestResult, status_code=200)
async def payments_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_dunning_signature: str | None = Header(default=None),
) -> IngestResult:
    """Receive a payment event, verify its signature, and run ingest + decisioning.

    Signing is enforced only when ``WEBHOOK_SIGNING_SECRET`` is set, so the demo
    works out of the box while production stays verified.
    """
    raw = await request.body()
    if not verify_signature(settings.webhook_signing_secret, raw, x_dunning_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        event = PaymentWebhookEvent.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Malformed event: {exc}") from exc

    return process_event(db, event)
