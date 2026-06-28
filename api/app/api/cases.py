"""Dunning queue + case detail, including human-in-the-loop controls."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DunningCase, DunningEvent, Message
from app.models.enums import Actor, CaseStatus, EventType, MessageStatus
from app.schemas.api import CaseDetail, CaseOverride, MessageEdit, MessageOut, QueuePage
from app.services import stats

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _now() -> datetime:
    return datetime.now(UTC)


@router.get("", response_model=QueuePage)
def list_queue(
    status: str | None = None, search: str | None = None, sort: str = "opened",
    limit: int = 100, offset: int = 0, db: Session = Depends(get_db),
) -> QueuePage:
    items, total, counts = stats.list_cases(
        db, status=status, search=search, sort=sort, limit=limit, offset=offset
    )
    return QueuePage(items=items, total=total, counts_by_status=counts)


@router.get("/{case_id}", response_model=CaseDetail)
def case_detail(case_id: str, db: Session = Depends(get_db)) -> CaseDetail:
    case = stats.get_case(db, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


def _get_case(db: Session, case_id: str) -> DunningCase:
    case = db.get(DunningCase, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


def _log(db, case, type_, title, *, reasoning=None, actor=Actor.HUMAN, message_id=None):
    db.add(DunningEvent(
        case_id=case.id, type=type_, title=title, reasoning=reasoning, actor=actor,
        message_id=message_id, occurred_at=_now(),
    ))


@router.post("/{case_id}/messages/{message_id}/approve", response_model=MessageOut)
def approve_message(case_id: str, message_id: str, db: Session = Depends(get_db)) -> MessageOut:
    msg = db.scalars(
        select(Message).where(Message.id == message_id, Message.case_id == case_id)
    ).first()
    if msg is None:
        raise HTTPException(404, "Message not found")
    case = _get_case(db, case_id)
    msg.status = MessageStatus.SENT
    msg.sent_at = _now()
    _log(db, case, EventType.MESSAGE_SENT, f"Operator approved & sent the {msg.tone.label.lower()}",
         reasoning="A human reviewed the agent's draft and approved it for sending.",
         message_id=msg.id)
    db.commit()
    db.refresh(msg)
    return stats._message_out(msg)


@router.patch("/{case_id}/messages/{message_id}", response_model=MessageOut)
def edit_message(
    case_id: str, message_id: str, payload: MessageEdit, db: Session = Depends(get_db)
) -> MessageOut:
    msg = db.scalars(
        select(Message).where(Message.id == message_id, Message.case_id == case_id)
    ).first()
    if msg is None:
        raise HTTPException(404, "Message not found")
    case = _get_case(db, case_id)
    if payload.subject is not None:
        msg.subject = payload.subject
    msg.body = payload.body
    msg.status = MessageStatus.EDITED
    _log(db, case, EventType.NOTE, "Operator edited the agent's draft",
         reasoning="A human revised the wording before it goes out — the agent's "
                   "draft was a starting point, not the final word.",
         message_id=msg.id)
    db.commit()
    db.refresh(msg)
    return stats._message_out(msg)


@router.post("/{case_id}/override", response_model=CaseDetail)
def override_case(case_id: str, payload: CaseOverride, db: Session = Depends(get_db)) -> CaseDetail:
    case = _get_case(db, case_id)
    action = payload.action
    note = payload.note or ""

    if action == "pause":
        case.status = CaseStatus.PAUSED
        case.next_action_label = "Paused by operator"
        _log(db, case, EventType.NOTE, "Operator paused this case",
             reasoning=note or "Automated dunning paused pending a human decision.")
    elif action == "resume":
        case.status = CaseStatus.IN_PROGRESS
        case.next_action_label = "Resumed — awaiting next step"
        _log(db, case, EventType.NOTE, "Operator resumed this case",
             reasoning=note or "Automated dunning resumed.")
    elif action == "escalate":
        case.status = CaseStatus.ESCALATED
        case.requires_human = True
        case.escalated_to = case.escalated_to or "credit_control"
        case.next_action_label = "Escalated by operator"
        _log(db, case, EventType.ESCALATED, "Operator escalated to credit control",
             reasoning=note or "A human escalated this case ahead of the automated ladder.")
    elif action == "resolve":
        case.status = CaseStatus.RECOVERED
        case.recovered_amount_minor = case.amount_at_risk_minor
        case.resolved_at = _now()
        case.requires_human = False
        case.next_action_label = None
        _log(db, case, EventType.RESOLVED, "Operator marked this case recovered",
             reasoning=note or "Resolved manually by a human (e.g. paid out-of-band).")
    elif action == "write_off":
        case.status = CaseStatus.WRITTEN_OFF
        case.resolved_at = _now()
        case.next_action_label = None
        _log(db, case, EventType.WRITTEN_OFF, "Operator wrote off this case",
             reasoning=note or "Written off by a human after review.")

    db.commit()
    detail = stats.get_case(db, case_id)
    assert detail is not None
    return detail
