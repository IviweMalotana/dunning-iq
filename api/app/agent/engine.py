"""The agent decision engine.

Given a freshly-failed payment, the engine opens a dunning case and produces the
agent's decisions — classification, retry plan, the first drafted message or an
escalation — each logged as a ``DunningEvent`` with plain-English reasoning.

In M2 the reasoning comes from the deterministic narrative generator, so a posted
webhook yields a fully classified, planned, drafted case with no API key. M3
swaps the reasoning source for live Claude behind the same ``Decision`` seam;
the billing guardrails in ``strategy.py`` are always honoured either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import strategy
from app.agent.strategy import Playbook, playbook_for
from app.models import (
    CaseStatus,
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
    SubscriptionStatus,
)
from app.seed import narrative
from app.seed.narrative import CaseContext


@dataclass
class Decision:
    """The reasoning content for one decision — the seam M3's LLM fills."""

    failure_code: FailureCode
    confidence: float
    classification_reasoning: str
    strategy_reasoning: str
    source: str  # "replay" | "claude"


def _now() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


def get_active_policy(db: Session) -> Policy:
    policy = db.scalars(select(Policy).where(Policy.is_active.is_(True))).first()
    if policy is None:
        policy = Policy()
        db.add(policy)
        db.flush()
    return policy


class DecisionEngine:
    """Deterministic decision engine. Subclassed by the live Claude engine (M3)."""

    source = "replay"

    def decide(self, ctx: CaseContext, pb: Playbook) -> Decision:
        """Produce the reasoning for a new case. Overridden by the live engine."""
        confidence = strategy.BASELINE_CONFIDENCE[ctx.failure_code]
        return Decision(
            failure_code=ctx.failure_code,
            confidence=confidence,
            classification_reasoning=narrative.classification_reasoning(ctx, pb),
            strategy_reasoning=narrative.strategy_reasoning(ctx, pb),
            source=self.source,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def open_case(self, db: Session, payment: Payment) -> DunningCase:
        """Open a dunning case for a failed payment and run the opening decisions."""
        policy = get_active_policy(db)
        sub: Subscription | None = payment.subscription
        customer = payment.customer
        code = payment.failure_code or FailureCode.CARD_DECLINED
        pb = playbook_for(code, max_retries=policy.max_retries, backoff_days=list(policy.backoff_days))
        ctx = CaseContext(
            first_name=customer.name.split()[0],
            full_name=customer.name,
            company=customer.company,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            plan_name=sub.plan_name if sub else "subscription",
            failure_code=code,
        )
        decision = self.decide(ctx, pb)
        opened = _now()

        case = DunningCase(
            customer_id=customer.id,
            subscription_id=sub.id if sub else None,
            triggering_payment_id=payment.id,
            status=CaseStatus.IN_PROGRESS,
            failure_code=code,
            amount_at_risk_minor=payment.amount_minor,
            currency=payment.currency,
            classification_confidence=round(decision.confidence, 2),
            total_steps=pb.total_steps,
            opened_at=opened,
            created_at=opened,
            plan={
                "failure_code": code.value,
                "recoverable": pb.recoverable,
                "max_attempts": pb.max_attempts,
                "backoff_days": pb.backoff_days[: pb.max_attempts],
                "escalate_after": pb.escalate_after,
                "escalation_target": pb.escalation_target,
                "summary": pb.summary,
                "decided_by": decision.source,
            },
        )
        db.add(case)
        db.flush()
        payment.case_id = case.id
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE

        self._add_event(
            db, case, EventType.CASE_OPENED, f"Payment failed — {ctx.amount} on {ctx.plan_name}",
            actor=Actor.SYSTEM, at=opened,
            detail={"failure_message": payment.failure_message, "failure_code": code.value},
        )
        self._add_event(
            db, case, EventType.CLASSIFICATION, f"Classified as {code.label}",
            reasoning=decision.classification_reasoning, at=opened + timedelta(seconds=3),
            detail={"confidence": case.classification_confidence, "source": decision.source},
        )

        if pb.max_attempts == 0:
            # Hard stop — escalate immediately (fraud / lost card).
            self._add_event(
                db, case, EventType.ESCALATED,
                f"Escalated to {narrative._target_phrase(pb.escalation_target)}",
                reasoning=decision.strategy_reasoning, at=opened + timedelta(seconds=5),
                detail=case.plan,
            )
            case.status = CaseStatus.ESCALATED
            case.requires_human = True
            case.escalated_to = pb.escalation_target
            case.next_action_label = f"Awaiting {narrative._target_phrase(pb.escalation_target)}"
            case.next_action_at = opened + timedelta(hours=4)
            return case

        # Retry plan + first drafted message (held for human approval by default).
        self._add_event(
            db, case, EventType.RETRY_SCHEDULED, "Retry plan set",
            reasoning=decision.strategy_reasoning, at=opened + timedelta(seconds=5),
            detail=case.plan,
        )
        gap = pb.backoff_days[0] if pb.backoff_days else 3
        tone = pb.tone_for_step(1)
        next_date = (opened + timedelta(days=gap)).strftime("%b %-d")
        subject, body = narrative.draft_message(ctx, tone, next_date if pb.recoverable else None)
        msg = Message(
            case_id=case.id, customer_id=customer.id, channel=MessageChannel.EMAIL, tone=tone,
            step_number=1, subject=subject, body=body,
            status=MessageStatus.SENT if policy.auto_send else MessageStatus.DRAFT,
            model=f"{decision.source}", created_at=opened + timedelta(seconds=6),
            sent_at=opened + timedelta(seconds=7) if policy.auto_send else None,
        )
        db.add(msg)
        db.flush()
        self._add_event(
            db, case, EventType.MESSAGE_DRAFTED, f"Drafted {tone.label.lower()} (step 1)",
            reasoning=narrative.message_reasoning(ctx, tone, 1), step=1,
            message_id=msg.id, at=opened + timedelta(seconds=6),
        )
        case.current_step = 1
        case.next_action_at = opened + timedelta(days=gap)
        case.next_action_label = (
            f"Retry #1 in {gap}d" if pb.recoverable else "Awaiting updated card"
        )
        return case

    def record_recovery(self, db: Session, case: DunningCase, payment: Payment) -> None:
        """A success arrived for an open case — close it as recovered."""
        at = _now()
        case.status = CaseStatus.RECOVERED
        case.recovered_amount_minor = payment.amount_minor
        case.resolved_at = at
        case.next_action_at = None
        case.next_action_label = None
        case.requires_human = False
        payment.case_id = case.id
        if case.subscription:
            case.subscription.status = SubscriptionStatus.ACTIVE
        ctx_amount = narrative.money(payment.amount_minor, payment.currency)
        self._add_event(
            db, case, EventType.RETRY_SUCCEEDED, f"Payment recovered — {ctx_amount} captured",
            reasoning=(
                f"A {ctx_amount} payment cleared for this account while the case was open. "
                f"Marking the dunning case recovered and standing down the retry ladder."
            ),
            payment_id=payment.id, at=at,
        )
        self._add_event(
            db, case, EventType.RESOLVED, "Case recovered",
            reasoning="Outstanding balance collected; subscription is active again.",
            at=at + timedelta(seconds=1),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _add_event(self, db, case, type_, title, *, reasoning=None, actor=Actor.AGENT,
                   step=None, detail=None, message_id=None, payment_id=None, at=None):
        db.add(DunningEvent(
            case_id=case.id, type=type_, title=title, reasoning=reasoning, actor=actor,
            step_number=step, detail=detail, message_id=message_id, payment_id=payment_id,
            occurred_at=at or _now(),
        ))


def get_engine() -> DecisionEngine:
    """Return the active engine. M3 returns the live Claude engine when keyed."""
    return DecisionEngine()
