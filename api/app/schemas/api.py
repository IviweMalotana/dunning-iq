"""Response/request models for the dashboard, queue, and case-detail APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Money(BaseModel):
    minor: int
    currency: str
    usd_minor: int  # reporting-currency equivalent for aggregation


class DashboardSummary(BaseModel):
    reporting_currency: str = "USD"
    at_risk_usd_minor: int
    recovered_usd_minor: int
    written_off_usd_minor: int
    recovery_rate: float          # recovered cases / all cases
    amount_recovery_rate: float   # recovered $ / (recovered + at-risk + written-off) $
    total_cases: int
    open_cases: int
    in_progress: int
    escalated: int
    recovered: int
    written_off: int
    paused: int
    needs_human: int
    avg_recovery_hours: float | None
    customers: int


class TimePoint(BaseModel):
    week: str            # ISO date of week start
    opened: int
    recovered: int
    recovered_usd_minor: int
    at_risk_usd_minor: int


class ReasonStat(BaseModel):
    code: str
    label: str
    count: int
    at_risk_usd_minor: int
    recovered_usd_minor: int
    recovery_rate: float


class QueueItem(BaseModel):
    id: str
    customer_name: str
    company: str | None
    email: str
    amount_minor: int
    currency: str
    amount_usd_minor: int
    failure_code: str
    failure_label: str
    status: str
    current_step: int
    total_steps: int
    next_action_label: str | None
    next_action_at: datetime | None
    opened_at: datetime
    resolved_at: datetime | None
    confidence: float | None
    requires_human: bool
    decided_by: str | None


class QueuePage(BaseModel):
    items: list[QueueItem]
    total: int
    counts_by_status: dict[str, int]


class EventOut(BaseModel):
    id: str
    type: str
    actor: str
    title: str
    reasoning: str | None
    detail: dict | None
    step_number: int | None
    message_id: str | None
    payment_id: str | None
    occurred_at: datetime


class MessageOut(BaseModel):
    id: str
    channel: str
    tone: str
    tone_label: str
    status: str
    step_number: int | None
    subject: str | None
    body: str
    model: str | None
    created_at: datetime
    sent_at: datetime | None


class CaseDetail(QueueItem):
    plan_name: str | None
    interval: str | None
    plan: dict | None
    recovered_minor: int
    escalated_to: str | None
    summary: str | None
    events: list[EventOut]
    messages: list[MessageOut]


# ── mutations (human-in-the-loop) ─────────────────────────────────────────────

class MessageEdit(BaseModel):
    subject: str | None = None
    body: str


class CaseOverride(BaseModel):
    action: Literal["pause", "resume", "escalate", "resolve", "write_off"]
    note: str | None = None
