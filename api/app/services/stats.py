"""Aggregate queries and serializers for the dashboard, queue, and case detail.

Multi-currency demo data is reported in a single base currency (USD) using fixed
FX rates — billing dashboards always report in one currency. Per-case views keep
the native currency; only aggregates are converted.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, DunningCase, DunningEvent, Message
from app.models.enums import CaseStatus, FailureCode, MessageTone
from app.schemas.api import (
    CaseDetail,
    DashboardSummary,
    EventOut,
    MessageOut,
    QueueItem,
    ReasonStat,
    TimePoint,
)

# Approximate FX → USD (demo reporting only).
_FX = {"USD": 1.0, "GBP": 1.27, "EUR": 1.08, "AUD": 0.66, "CAD": 0.73}


def to_usd_minor(amount_minor: int, currency: str) -> int:
    return round(amount_minor * _FX.get(currency, 1.0))


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC for safe math."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ── dashboard ─────────────────────────────────────────────────────────────────

def dashboard_summary(db: Session) -> DashboardSummary:
    cases = db.scalars(select(DunningCase)).all()
    counts = Counter(c.status for c in cases)

    at_risk = sum(to_usd_minor(c.amount_at_risk_minor, c.currency) for c in cases if c.status.is_open)
    recovered = sum(to_usd_minor(c.recovered_amount_minor, c.currency) for c in cases)
    written_off = sum(
        to_usd_minor(c.amount_at_risk_minor, c.currency)
        for c in cases if c.status is CaseStatus.WRITTEN_OFF
    )

    total = len(cases) or 1
    denom = recovered + at_risk + written_off or 1

    rec_hours: list[float] = []
    for c in cases:
        if c.status is CaseStatus.RECOVERED and c.resolved_at:
            delta = _aware(c.resolved_at) - _aware(c.opened_at)
            rec_hours.append(delta.total_seconds() / 3600)

    customers = db.scalar(select(func.count()).select_from(Customer)) or 0

    return DashboardSummary(
        at_risk_usd_minor=at_risk,
        recovered_usd_minor=recovered,
        written_off_usd_minor=written_off,
        recovery_rate=counts[CaseStatus.RECOVERED] / total,
        amount_recovery_rate=recovered / denom,
        total_cases=len(cases),
        open_cases=sum(1 for c in cases if c.status.is_open),
        in_progress=counts[CaseStatus.IN_PROGRESS],
        escalated=counts[CaseStatus.ESCALATED],
        recovered=counts[CaseStatus.RECOVERED],
        written_off=counts[CaseStatus.WRITTEN_OFF],
        paused=counts[CaseStatus.PAUSED],
        needs_human=sum(1 for c in cases if c.requires_human),
        avg_recovery_hours=round(sum(rec_hours) / len(rec_hours), 1) if rec_hours else None,
        customers=customers,
    )


def dashboard_timeseries(db: Session, weeks: int = 12) -> list[TimePoint]:
    cases = db.scalars(select(DunningCase)).all()
    today = _now().date()
    # Monday of the current week, then walk back `weeks`.
    start_monday = today - timedelta(days=today.weekday())
    buckets = [start_monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]

    opened: dict = defaultdict(int)
    recovered: dict = defaultdict(int)
    rec_amt: dict = defaultdict(int)
    risk_amt: dict = defaultdict(int)

    def wk(d) -> object:
        monday = d - timedelta(days=d.weekday())
        return monday

    for c in cases:
        ob = wk(_aware(c.opened_at).date())
        if buckets[0] <= ob <= buckets[-1]:
            opened[ob] += 1
            if c.status.is_open:
                risk_amt[ob] += to_usd_minor(c.amount_at_risk_minor, c.currency)
        if c.status is CaseStatus.RECOVERED and c.resolved_at:
            rb = wk(_aware(c.resolved_at).date())
            if buckets[0] <= rb <= buckets[-1]:
                recovered[rb] += 1
                rec_amt[rb] += to_usd_minor(c.recovered_amount_minor, c.currency)

    return [
        TimePoint(
            week=b.isoformat(), opened=opened[b], recovered=recovered[b],
            recovered_usd_minor=rec_amt[b], at_risk_usd_minor=risk_amt[b],
        )
        for b in buckets
    ]


def dashboard_by_reason(db: Session) -> list[ReasonStat]:
    cases = db.scalars(select(DunningCase)).all()
    by: dict = defaultdict(lambda: {"count": 0, "risk": 0, "rec": 0, "recovered": 0})
    for c in cases:
        b = by[c.failure_code]
        b["count"] += 1
        if c.status.is_open:
            b["risk"] += to_usd_minor(c.amount_at_risk_minor, c.currency)
        if c.status is CaseStatus.RECOVERED:
            b["recovered"] += 1
            b["rec"] += to_usd_minor(c.recovered_amount_minor, c.currency)

    out = [
        ReasonStat(
            code=code.value, label=code.label, count=b["count"],
            at_risk_usd_minor=b["risk"], recovered_usd_minor=b["rec"],
            recovery_rate=(b["recovered"] / b["count"]) if b["count"] else 0.0,
        )
        for code, b in by.items()
    ]
    return sorted(out, key=lambda r: r.count, reverse=True)


# ── queue + case detail ───────────────────────────────────────────────────────

def _queue_item(c: DunningCase) -> QueueItem:
    cust = c.customer
    return QueueItem(
        id=c.id,
        customer_name=cust.name,
        company=cust.company,
        email=cust.email,
        amount_minor=c.amount_at_risk_minor,
        currency=c.currency,
        amount_usd_minor=to_usd_minor(c.amount_at_risk_minor, c.currency),
        failure_code=c.failure_code.value,
        failure_label=FailureCode(c.failure_code).label,
        status=c.status.value,
        current_step=c.current_step,
        total_steps=c.total_steps,
        next_action_label=c.next_action_label,
        next_action_at=c.next_action_at,
        opened_at=c.opened_at,
        resolved_at=c.resolved_at,
        confidence=c.classification_confidence,
        requires_human=c.requires_human,
        decided_by=(c.plan or {}).get("decided_by"),
    )


def list_cases(
    db: Session, status: str | None = None, search: str | None = None,
    sort: str = "opened", limit: int = 100, offset: int = 0,
) -> tuple[list[QueueItem], int, dict[str, int]]:
    cases = db.scalars(
        select(DunningCase).options(selectinload(DunningCase.customer))
    ).all()
    counts = Counter(c.status.value for c in cases)

    filtered = cases
    if status and status != "all":
        if status == "open":
            filtered = [c for c in filtered if c.status.is_open]
        else:
            filtered = [c for c in filtered if c.status.value == status]
    if search:
        q = search.lower()
        filtered = [
            c for c in filtered
            if q in c.customer.name.lower()
            or q in (c.customer.company or "").lower()
            or q in c.customer.email.lower()
        ]

    keys = {
        "opened": lambda c: _aware(c.opened_at),
        "amount": lambda c: to_usd_minor(c.amount_at_risk_minor, c.currency),
        "next": lambda c: _aware(c.next_action_at) or _aware(c.opened_at),
    }
    reverse = sort != "next"
    filtered.sort(key=keys.get(sort, keys["opened"]), reverse=reverse)

    total = len(filtered)
    page = filtered[offset: offset + limit]
    return [_queue_item(c) for c in page], total, dict(counts)


def _event_out(e: DunningEvent) -> EventOut:
    return EventOut(
        id=e.id, type=e.type.value, actor=e.actor.value, title=e.title,
        reasoning=e.reasoning, detail=e.detail, step_number=e.step_number,
        message_id=e.message_id, payment_id=e.payment_id, occurred_at=e.occurred_at,
    )


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id, channel=m.channel.value, tone=m.tone.value,
        tone_label=MessageTone(m.tone).label, status=m.status.value,
        step_number=m.step_number, subject=m.subject, body=m.body,
        model=m.model, created_at=m.created_at, sent_at=m.sent_at,
    )


def get_case(db: Session, case_id: str) -> CaseDetail | None:
    c = db.scalars(
        select(DunningCase)
        .where(DunningCase.id == case_id)
        .options(
            selectinload(DunningCase.customer),
            selectinload(DunningCase.subscription),
            selectinload(DunningCase.events),
            selectinload(DunningCase.messages),
        )
    ).first()
    if c is None:
        return None
    base = _queue_item(c).model_dump()
    return CaseDetail(
        **base,
        plan_name=c.subscription.plan_name if c.subscription else None,
        interval=c.subscription.interval if c.subscription else None,
        plan=c.plan,
        recovered_minor=c.recovered_amount_minor,
        escalated_to=c.escalated_to,
        summary=(c.plan or {}).get("summary"),
        events=[_event_out(e) for e in c.events],
        messages=[_message_out(m) for m in c.messages],
    )
