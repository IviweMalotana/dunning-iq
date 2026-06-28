"""Seed a realistic, story-driven demo dataset.

Run with:  uv run python -m app.seed.run  [--force]

Generates a few hundred customers with a believable spread of payment failures
and dunning outcomes — some recovered, some escalated, some still in progress —
so the dashboard looks alive on first load with zero setup.
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.strategy import playbook_for
from app.db.session import SessionLocal, engine
from app.models import (
    CaseStatus,
    Customer,
    DunningCase,
    DunningEvent,
    Message,
    Payment,
    Policy,
    Subscription,
)
from app.models.enums import (
    Actor,
    EventType,
    FailureCode,
    MessageChannel,
    MessageStatus,
    PaymentStatus,
    SubscriptionStatus,
)
from app.seed import catalog, narrative
from app.seed.narrative import CaseContext

RNG = random.Random(7)
NOW = datetime.now(UTC)
NUM_CUSTOMERS = 320
# Share of customers that hit at least one failed payment / dunning case.
FAILURE_RATE = 0.30

CONFIDENCE = {
    FailureCode.INSUFFICIENT_FUNDS: 0.96,
    FailureCode.EXPIRED_CARD: 0.99,
    FailureCode.DO_NOT_HONOR: 0.72,
    FailureCode.CARD_DECLINED: 0.78,
    FailureCode.LOST_OR_STOLEN: 0.97,
    FailureCode.AUTHENTICATION_REQUIRED: 0.93,
    FailureCode.PROCESSING_ERROR: 0.88,
    FailureCode.FRAUD_SUSPECTED: 0.94,
}

# Status distribution per failure-code family — drives a lively, believable mix.
_SOFT = {CaseStatus.RECOVERED: 62, CaseStatus.IN_PROGRESS: 22,
         CaseStatus.ESCALATED: 8, CaseStatus.WRITTEN_OFF: 5, CaseStatus.PAUSED: 3}
_ACTION = {CaseStatus.RECOVERED: 45, CaseStatus.IN_PROGRESS: 30,
           CaseStatus.ESCALATED: 15, CaseStatus.WRITTEN_OFF: 8, CaseStatus.PAUSED: 2}
_HARD = {CaseStatus.ESCALATED: 55, CaseStatus.WRITTEN_OFF: 30,
         CaseStatus.IN_PROGRESS: 11, CaseStatus.RECOVERED: 2, CaseStatus.PAUSED: 2}

_STATUS_MIX = {
    FailureCode.INSUFFICIENT_FUNDS: _SOFT,
    FailureCode.PROCESSING_ERROR: _SOFT,
    FailureCode.AUTHENTICATION_REQUIRED: _ACTION,
    FailureCode.DO_NOT_HONOR: _ACTION,
    FailureCode.CARD_DECLINED: _ACTION,
    FailureCode.EXPIRED_CARD: _ACTION,
    FailureCode.LOST_OR_STOLEN: _HARD,
    FailureCode.FRAUD_SUSPECTED: _HARD,
}


def _weighted(pairs: list[tuple]) -> object:
    items = [p[0] for p in pairs]
    weights = [p[1] for p in pairs]
    return RNG.choices(items, weights=weights, k=1)[0]


def _weighted_dict(d: dict) -> object:
    return _weighted(list(d.items()))


def _ext_id(prefix: str) -> str:
    return prefix + "".join(RNG.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=14))


def _make_customer(i: int) -> tuple[Customer, Subscription]:
    first = RNG.choice(catalog.FIRST_NAMES)
    last = RNG.choice(catalog.LAST_NAMES)
    name = f"{first} {last}"
    plan = _weighted([(p, p[3]) for p in catalog.PLANS])
    plan_name, amount, segment = plan[0], plan[1], plan[2]

    has_company = segment != "starter" or RNG.random() < 0.5
    company = None
    if has_company:
        company = f"{RNG.choice(catalog.COMPANY_PREFIX)} {RNG.choice(catalog.COMPANY_SUFFIX)}"
    domain = (company or name).lower().replace(" ", "").replace(",", "")[:18]
    email = f"{first.lower()}.{last.lower()}@{domain}.com"
    country = RNG.choice(catalog.COUNTRIES)
    currency = {"GB": "GBP", "DE": "EUR", "FR": "EUR", "NL": "EUR", "IE": "EUR",
                "AU": "AUD", "CA": "CAD"}.get(country, "USD")
    created = NOW - timedelta(days=RNG.randint(40, 900))

    cust = Customer(
        external_id=_ext_id("cus_"), name=name, email=email, company=company,
        segment=segment, country=country, created_at=created,
    )
    interval = "year" if "annual" in plan_name else "month"
    sub = Subscription(
        external_id=_ext_id("sub_"), customer=cust, plan_name=plan_name,
        amount_minor=amount, currency=currency, interval=interval,
        status=SubscriptionStatus.ACTIVE,
        current_period_end=NOW + timedelta(days=RNG.randint(2, 28)), created_at=created,
    )
    return cust, sub


def _succeeded_payment(cust: Customer, sub: Subscription, when: datetime) -> Payment:
    return Payment(
        external_id=_ext_id("pay_"), customer=cust, subscription_id=sub.id,
        amount_minor=sub.amount_minor, currency=sub.currency,
        status=PaymentStatus.SUCCEEDED, attempt_number=1,
        processor=RNG.choice(["stripe", "stripe", "paddle"]), created_at=when,
    )


def _build_case(db: Session, cust: Customer, sub: Subscription) -> None:
    code = _weighted(catalog.FAILURE_WEIGHTS)
    status: CaseStatus = _weighted_dict(_STATUS_MIX[code])
    pb = playbook_for(code, max_retries=4, backoff_days=[2, 3, 5, 7])
    ctx = CaseContext(
        first_name=cust.name.split()[0], full_name=cust.name, company=cust.company,
        amount_minor=sub.amount_minor, currency=sub.currency, plan_name=sub.plan_name,
        failure_code=code,
    )

    age_days = RNG.randint(1, 88)
    opened = NOW - timedelta(days=age_days, hours=RNG.randint(0, 20))
    sub.status = SubscriptionStatus.PAST_DUE

    case = DunningCase(
        customer=cust, subscription_id=sub.id, status=status, failure_code=code,
        amount_at_risk_minor=sub.amount_minor, currency=sub.currency,
        classification_confidence=round(
            min(0.99, max(0.5, CONFIDENCE[code] + RNG.uniform(-0.04, 0.02))), 2
        ),
        total_steps=pb.total_steps, opened_at=opened, created_at=opened,
        plan={
            "failure_code": code.value,
            "recoverable": pb.recoverable,
            "max_attempts": pb.max_attempts,
            "backoff_days": pb.backoff_days[: pb.max_attempts],
            "escalate_after": pb.escalate_after,
            "escalation_target": pb.escalation_target,
            "summary": pb.summary,
        },
    )
    db.add(case)
    db.flush()  # assign case.id

    # Triggering failed payment.
    failed_pay = Payment(
        external_id=_ext_id("pay_"), customer=cust, subscription_id=sub.id,
        amount_minor=sub.amount_minor, currency=sub.currency,
        status=PaymentStatus.FAILED, failure_code=code,
        failure_message=catalog.DECLINE_MESSAGES[code], attempt_number=1,
        processor=RNG.choice(["stripe", "stripe", "paddle"]), case_id=case.id, created_at=opened,
    )
    db.add(failed_pay)
    case.triggering_payment_id = failed_pay.id

    events: list[DunningEvent] = []
    t = opened

    def ev(type_: EventType, title: str, *, reasoning=None, actor=Actor.AGENT,
           step=None, detail=None, dt_secs=0, message_id=None, payment_id=None):
        nonlocal t
        t = t + timedelta(seconds=dt_secs)
        events.append(DunningEvent(
            case_id=case.id, type=type_, title=title, reasoning=reasoning, actor=actor,
            step_number=step, detail=detail, occurred_at=t, message_id=message_id,
            payment_id=payment_id,
        ))

    ev(EventType.CASE_OPENED, f"Payment failed — {ctx.amount} on {sub.plan_name}",
       actor=Actor.SYSTEM, detail={"failure_message": catalog.DECLINE_MESSAGES[code]})
    ev(EventType.CLASSIFICATION, f"Classified as {code.label}",
       reasoning=narrative.classification_reasoning(ctx, pb),
       detail={"confidence": case.classification_confidence, "failure_code": code.value}, dt_secs=3)
    ev(EventType.RETRY_SCHEDULED if pb.max_attempts else EventType.ESCALATED,
       "Retry plan set" if pb.max_attempts else "No retries — routing to human",
       reasoning=narrative.strategy_reasoning(ctx, pb), detail=case.plan, dt_secs=2)

    # Decide how far the ladder progresses based on the terminal status.
    n = pb.max_attempts
    recover_step = None
    if status is CaseStatus.RECOVERED:
        recover_step = RNG.choices(range(1, max(n, 1) + 1),
                                   weights=[max(1, 6 - i) for i in range(max(n, 1))])[0] \
            if n else 1
    reached = {
        CaseStatus.RECOVERED: recover_step or 1,
        CaseStatus.IN_PROGRESS: RNG.randint(1, max(1, n - 1)) if n > 1 else 1,
        CaseStatus.PAUSED: RNG.randint(1, max(1, n - 1)) if n > 1 else 1,
        CaseStatus.ESCALATED: max(n, 1),
        CaseStatus.WRITTEN_OFF: max(n, 1),
    }[status]

    for step in range(1, reached + 1):
        gap_days = pb.backoff_days[step - 1] if step - 1 < len(pb.backoff_days) else 5
        # Customer message at this step (draft if it's the pending next action).
        tone = pb.tone_for_step(step)
        is_pending = status in (CaseStatus.IN_PROGRESS, CaseStatus.PAUSED) and step == reached
        next_date = (t + timedelta(days=gap_days)).strftime("%b %-d")
        subject, body = narrative.draft_message(ctx, tone, next_date if pb.recoverable else None)
        msg = Message(
            case_id=case.id, customer_id=cust.id, channel=MessageChannel.EMAIL, tone=tone,
            step_number=step, subject=subject, body=body,
            status=MessageStatus.DRAFT if is_pending else MessageStatus.SENT,
            model="claude-opus-4-8 (replay)",
            created_at=t + timedelta(seconds=4),
            sent_at=None if is_pending else t + timedelta(seconds=5),
        )
        db.add(msg)
        db.flush()
        ev(EventType.MESSAGE_DRAFTED, f"Drafted {tone.label.lower()} (step {step})",
           reasoning=narrative.message_reasoning(ctx, tone, step), step=step,
           message_id=msg.id, dt_secs=4)
        if not is_pending:
            ev(EventType.MESSAGE_SENT, f"Sent {tone.label.lower()} to {cust.email}",
               actor=Actor.SYSTEM, step=step, message_id=msg.id, dt_secs=1)

        # Retry attempt (only if the playbook retries).
        if pb.max_attempts:
            succeeded = status is CaseStatus.RECOVERED and step == recover_step
            t = t + timedelta(days=gap_days)
            ev(EventType.RETRY_ATTEMPTED, f"Retry #{step} — {ctx.amount}",
               actor=Actor.SYSTEM, step=step,
               detail={"attempt": step + 1}, dt_secs=0)
            if succeeded:
                ok_pay = _succeeded_payment(cust, sub, t)
                ok_pay.attempt_number = step + 1
                ok_pay.case_id = case.id
                db.add(ok_pay)
                ev(EventType.RETRY_SUCCEEDED, f"Retry #{step} succeeded — {ctx.amount} captured",
                   reasoning=narrative.retry_reasoning(ctx, step, True), step=step,
                   payment_id=ok_pay.id, dt_secs=2)
                break
            else:
                ev(EventType.RETRY_FAILED, f"Retry #{step} failed — {code.label}",
                   reasoning=narrative.retry_reasoning(ctx, step, False), step=step, dt_secs=2)

    # Terminal transitions.
    case.current_step = reached
    if status is CaseStatus.RECOVERED:
        if not pb.max_attempts:
            # Hard decline recovered via the customer adding a new card.
            t = t + timedelta(days=RNG.randint(1, 6))
            ok_pay = _succeeded_payment(cust, sub, t)
            ok_pay.case_id = case.id
            db.add(ok_pay)
            ev(EventType.RETRY_SUCCEEDED, f"New card added — {ctx.amount} captured",
               reasoning="Customer updated their payment method via the link in our message; the "
                         "charge cleared on the new card. Recovered without human involvement.",
               payment_id=ok_pay.id, dt_secs=2)
        case.recovered_amount_minor = sub.amount_minor
        case.resolved_at = t
        sub.status = SubscriptionStatus.ACTIVE
        ev(EventType.RESOLVED, "Case recovered", reasoning=narrative.resolution_reasoning(ctx, reached),
           dt_secs=1)
        case.next_action_label = None

    elif status is CaseStatus.ESCALATED:
        ev(EventType.ESCALATED, f"Escalated to {narrative._target_phrase(pb.escalation_target)}",
           reasoning=narrative.escalation_reasoning(ctx, pb), dt_secs=2)
        case.escalated_to = pb.escalation_target
        case.requires_human = True
        case.next_action_label = f"Awaiting {narrative._target_phrase(pb.escalation_target)}"
        case.next_action_at = NOW + timedelta(hours=RNG.randint(2, 36))

    elif status is CaseStatus.WRITTEN_OFF:
        t = t + timedelta(days=RNG.randint(1, 5))
        ev(EventType.WRITTEN_OFF, "Written off", reasoning=narrative.writeoff_reasoning(ctx), dt_secs=1)
        case.resolved_at = t
        sub.status = SubscriptionStatus.CANCELED
        case.next_action_label = None

    elif status is CaseStatus.PAUSED:
        ev(EventType.NOTE, "Dunning paused", actor=Actor.HUMAN,
           reasoning="Paused by an operator — customer replied and is sorting a new card this week. "
                     "Holding automated messages so we don't talk over a live conversation.")
        case.next_action_label = "Paused — operator follow-up"
        case.next_action_at = NOW + timedelta(days=RNG.randint(1, 4))

    else:  # IN_PROGRESS
        nxt = pb.tone_for_step(reached + 1) if reached < pb.total_steps else None
        if pb.max_attempts and reached < pb.max_attempts:
            case.next_action_label = f"Retry #{reached + 1} scheduled"
        elif nxt:
            case.next_action_label = f"Send {nxt.label.lower()}"
        else:
            case.next_action_label = "Awaiting outcome"
        case.next_action_at = NOW + timedelta(hours=RNG.randint(3, 60))

    db.add_all(events)


def _ensure_policy(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Policy)):
        return
    db.add(Policy())


def seed(force: bool = False) -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(Customer))
        if existing and not force:
            print(f"↩  Already seeded ({existing} customers). Use `make reset` or --force to rebuild.")
            return
        if existing and force:
            for model in (DunningEvent, Message, Payment, DunningCase, Subscription, Customer, Policy):
                db.query(model).delete()
            db.commit()

        _ensure_policy(db)

        n_cases = 0
        for i in range(NUM_CUSTOMERS):
            cust, sub = _make_customer(i)
            db.add(cust)
            db.add(sub)
            db.flush()
            if RNG.random() < FAILURE_RATE:
                _build_case(db, cust, sub)
                n_cases += 1
            else:
                # Healthy account: a recent successful charge.
                db.add(_succeeded_payment(cust, sub, NOW - timedelta(days=RNG.randint(1, 25))))
            if i % 50 == 0:
                db.flush()

        db.commit()
        print(f"✅ Seeded {NUM_CUSTOMERS} customers, {n_cases} dunning cases.")


if __name__ == "__main__":
    # Make sure tables exist even if migrations weren't run (best-effort).
    from app.db.session import Base
    Base.metadata.create_all(engine)
    seed(force="--force" in sys.argv)
