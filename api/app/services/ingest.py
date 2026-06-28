"""Ingest a payment webhook: upsert entities, then drive the decision engine.

This is the single entry point both the live webhook endpoint and the simulator
call, so the same code path runs whether events come from a real PSP or the
built-in generator.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.engine import DecisionEngine, get_engine
from app.models import (
    CaseStatus,
    Customer,
    DunningCase,
    DunningEvent,
    Payment,
    Subscription,
)
from app.models.enums import Actor, EventType, PaymentStatus, SubscriptionStatus
from app.schemas.webhooks import (
    CustomerPayload,
    IngestResult,
    PaymentWebhookEvent,
    SubscriptionPayload,
    normalise_failure_code,
)
from app.seed import narrative

_OPEN_STATUSES = [CaseStatus.IN_PROGRESS, CaseStatus.ESCALATED, CaseStatus.PAUSED]


def _upsert_customer(db: Session, p: CustomerPayload) -> Customer:
    cust = db.scalars(select(Customer).where(Customer.external_id == p.external_id)).first()
    if cust is None:
        cust = Customer(
            external_id=p.external_id, name=p.name, email=p.email,
            company=p.company, country=p.country,
        )
        db.add(cust)
        db.flush()
    return cust


def _upsert_subscription(db: Session, p: SubscriptionPayload, customer: Customer) -> Subscription:
    sub = db.scalars(select(Subscription).where(Subscription.external_id == p.external_id)).first()
    if sub is None:
        sub = Subscription(
            external_id=p.external_id, customer_id=customer.id, plan_name=p.plan_name,
            amount_minor=p.amount_minor, currency=p.currency, interval=p.interval,
            status=SubscriptionStatus.ACTIVE,
        )
        db.add(sub)
        db.flush()
    return sub


def _open_case_for_subscription(db: Session, sub_id: str) -> DunningCase | None:
    return db.scalars(
        select(DunningCase)
        .where(DunningCase.subscription_id == sub_id, DunningCase.status.in_(_OPEN_STATUSES))
        .order_by(DunningCase.opened_at.desc())
    ).first()


def process_event(
    db: Session, event: PaymentWebhookEvent, engine: DecisionEngine | None = None
) -> IngestResult:
    engine = engine or get_engine()
    customer = _upsert_customer(db, event.data.customer)
    sub = _upsert_subscription(db, event.data.subscription, customer)
    pp = event.data.payment

    # Idempotency: a re-delivered event must not double-process.
    existing = db.scalars(select(Payment).where(Payment.external_id == pp.external_id)).first()
    if existing is not None:
        return IngestResult(
            event_id=event.id, event_type=event.type, customer_id=customer.id,
            payment_id=existing.id, case_id=existing.case_id,
            case_status=None, action="ignored_duplicate",
            detail=f"Payment {pp.external_id} already processed.",
        )

    if event.type == "payment_failed":
        return _handle_failure(db, event, customer, sub, engine)
    return _handle_success(db, event, customer, sub)


def _handle_failure(db, event, customer, sub, engine) -> IngestResult:
    pp = event.data.payment
    code = normalise_failure_code(pp.failure_code)
    payment = Payment(
        external_id=pp.external_id, customer_id=customer.id, subscription_id=sub.id,
        amount_minor=pp.amount_minor, currency=pp.currency, status=PaymentStatus.FAILED,
        failure_code=code, failure_message=pp.failure_message, processor=pp.processor,
        created_at=datetime.now(UTC),
    )
    db.add(payment)
    db.flush()

    open_case = _open_case_for_subscription(db, sub.id)
    if open_case is not None:
        # Another failure on an already-open case — record it, don't re-open.
        payment.case_id = open_case.id
        amount = narrative.money(pp.amount_minor, pp.currency)
        db.add(DunningEvent(
            case_id=open_case.id, type=EventType.RETRY_FAILED, actor=Actor.SYSTEM,
            title=f"Further failure — {amount} ({code.label})",
            reasoning="A new failed charge landed while this case was still open; folding it into "
                      "the existing recovery effort rather than starting a parallel case.",
            payment_id=payment.id, occurred_at=datetime.now(UTC),
        ))
        db.commit()
        return IngestResult(
            event_id=event.id, event_type=event.type, customer_id=customer.id,
            payment_id=payment.id, case_id=open_case.id, case_status=open_case.status.value,
            action="appended_to_open_case",
            detail=f"Recorded another {code.label} failure on open case {open_case.id}.",
        )

    case = engine.open_case(db, payment)
    db.commit()
    return IngestResult(
        event_id=event.id, event_type=event.type, customer_id=customer.id,
        payment_id=payment.id, case_id=case.id, case_status=case.status.value,
        action="opened_case",
        detail=f"Opened case, classified as {code.label} "
               f"({case.classification_confidence:.0%} conf), plan set.",
    )


def _handle_success(db, event, customer, sub) -> IngestResult:
    pp = event.data.payment
    payment = Payment(
        external_id=pp.external_id, customer_id=customer.id, subscription_id=sub.id,
        amount_minor=pp.amount_minor, currency=pp.currency, status=PaymentStatus.SUCCEEDED,
        processor=pp.processor, created_at=datetime.now(UTC),
    )
    db.add(payment)
    db.flush()

    open_case = _open_case_for_subscription(db, sub.id)
    if open_case is not None:
        get_engine().record_recovery(db, open_case, payment)
        sub.status = SubscriptionStatus.ACTIVE
        db.commit()
        return IngestResult(
            event_id=event.id, event_type=event.type, customer_id=customer.id,
            payment_id=payment.id, case_id=open_case.id, case_status=open_case.status.value,
            action="recovered_case",
            detail=f"Open case {open_case.id} recovered.",
        )

    db.commit()
    return IngestResult(
        event_id=event.id, event_type=event.type, customer_id=customer.id,
        payment_id=payment.id, case_id=None, case_status=None, action="recorded_payment",
        detail="Successful charge with no open case — normal renewal.",
    )
