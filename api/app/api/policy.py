"""Editable retry policy + message tone, with a live agent preview.

The preview lets a viewer change the rules and immediately see how the agent's
plan and drafted message change — without saving or firing an event.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.engine import get_active_policy, get_engine
from app.agent.strategy import playbook_for
from app.db.session import get_db
from app.models import Policy
from app.models.enums import FailureCode, MessageTone
from app.schemas.api import (
    PolicyOut,
    PolicyPreview,
    PolicyPreviewRequest,
    PolicyUpdate,
    PreviewMessage,
)
from app.seed.narrative import CaseContext

router = APIRouter(prefix="/api/policy", tags=["policy"])

# A representative account used only to render the preview.
_SAMPLE = {
    "first_name": "Priya", "full_name": "Priya Okafor", "company": "Harbor Systems",
    "amount_minor": 9900, "currency": "USD", "plan_name": "Growth (monthly)",
}


def _out(p: Policy) -> PolicyOut:
    return PolicyOut(
        id=p.id, name=p.name, is_active=p.is_active, max_retries=p.max_retries,
        backoff_days=list(p.backoff_days), retry_window_days=p.retry_window_days,
        escalate_after_step=p.escalate_after_step, base_tone=p.base_tone,
        brand_voice=p.brand_voice, auto_send=p.auto_send, updated_at=p.updated_at,
    )


@router.get("", response_model=PolicyOut)
def get_policy(db: Session = Depends(get_db)) -> PolicyOut:
    return _out(get_active_policy(db))


@router.patch("", response_model=PolicyOut)
def update_policy(payload: PolicyUpdate, db: Session = Depends(get_db)) -> PolicyOut:
    policy = get_active_policy(db)
    data = payload.model_dump(exclude_unset=True)
    if "max_retries" in data:
        data["max_retries"] = max(0, min(8, data["max_retries"]))
    if "backoff_days" in data and data["backoff_days"] is not None:
        data["backoff_days"] = [max(0, min(60, int(d))) for d in data["backoff_days"]][:8]
    if data.get("base_tone") and data["base_tone"] not in set(MessageTone):
        raise HTTPException(422, f"Unknown tone '{data['base_tone']}'")
    for field, value in data.items():
        setattr(policy, field, value)
    policy.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(policy)
    return _out(policy)


@router.post("/preview", response_model=PolicyPreview)
def preview(payload: PolicyPreviewRequest, db: Session = Depends(get_db)) -> PolicyPreview:
    policy = get_active_policy(db)
    try:
        code = FailureCode(payload.failure_code)
    except ValueError as exc:
        raise HTTPException(422, f"Unknown failure code '{payload.failure_code}'") from exc

    max_retries = payload.max_retries if payload.max_retries is not None else policy.max_retries
    backoff = payload.backoff_days if payload.backoff_days is not None else list(policy.backoff_days)
    base_tone = payload.base_tone or policy.base_tone
    brand_voice = payload.brand_voice if payload.brand_voice is not None else policy.brand_voice
    auto_send = payload.auto_send if payload.auto_send is not None else policy.auto_send

    pb = playbook_for(code, max_retries=max_retries, backoff_days=backoff)
    ctx = CaseContext(failure_code=code, **_SAMPLE)

    tone: MessageTone | None = None
    next_date = None
    if pb.max_attempts:
        try:
            tone = MessageTone(base_tone)
        except ValueError:
            tone = pb.tone_for_step(1)
        gap = pb.backoff_days[0] if pb.backoff_days else 3
        next_date = (datetime.now(UTC) + timedelta(days=gap)).strftime("%b %-d")

    decision = get_engine().analyze(
        ctx, pb, tone=tone, next_date=next_date, brand_voice=brand_voice
    )

    message = None
    if decision.message_body is not None and tone is not None:
        message = PreviewMessage(
            tone=tone.value, tone_label=tone.label,
            subject=decision.message_subject, body=decision.message_body,
        )

    return PolicyPreview(
        failure_code=code.value, failure_label=code.label,
        recoverable=pb.recoverable, needs_customer_action=pb.needs_customer_action,
        max_attempts=pb.max_attempts, backoff_days=pb.backoff_days[: pb.max_attempts],
        escalate_after=pb.escalate_after, escalation_target=pb.escalation_target,
        summary=pb.summary, confidence=decision.confidence,
        classification_reasoning=decision.classification_reasoning,
        strategy_reasoning=decision.strategy_reasoning,
        message=message, auto_send=auto_send, decided_by=decision.source,
    )
