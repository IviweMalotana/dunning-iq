"""Per-failure-code recovery playbooks — the agent's decision spine.

Pure, deterministic domain logic shared by the seed (replay) and the live
Claude engine (M3). The LLM produces the *reasoning and the customer prose*; this
module encodes the hard billing rules that keep retries sane (don't hammer a
stolen card, align insufficient-funds retries to paydays, escalate fraud
immediately). Keeping the guardrails here means the agent can be expressive
without ever doing something a billing operator would veto.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import FailureCode, MessageTone

# Default tone escalation ladder, trimmed per playbook length.
TONE_LADDER: list[MessageTone] = [
    MessageTone.FRIENDLY_REMINDER,
    MessageTone.FIRM_REMINDER,
    MessageTone.URGENT,
    MessageTone.FINAL_NOTICE,
    MessageTone.CREDIT_CONTROL,
]


@dataclass
class Playbook:
    failure_code: FailureCode
    recoverable: bool
    needs_customer_action: bool
    max_attempts: int
    backoff_days: list[int]
    escalate_after: int  # 1-indexed step after which to escalate; 0 = immediate
    escalation_target: str | None  # "credit_control" | "human_review" | None
    summary: str
    tone_ladder: list[MessageTone] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return max(self.max_attempts, 1)

    def tone_for_step(self, step: int) -> MessageTone:
        ladder = self.tone_ladder or TONE_LADDER
        idx = min(step - 1, len(ladder) - 1)
        return ladder[max(idx, 0)]


def playbook_for(code: FailureCode, *, max_retries: int, backoff_days: list[int]) -> Playbook:
    """Resolve the recovery playbook for a failure code under a given policy.

    Soft declines lean on the configured policy cadence; hard declines override
    it because retrying a closed/expired card just burns processor fees.
    """
    base_backoff = list(backoff_days) or [1, 3, 5, 7]

    if code is FailureCode.INSUFFICIENT_FUNDS:
        # Most recoverable failure. Space retries toward likely pay cycles.
        return Playbook(
            code, recoverable=True, needs_customer_action=False,
            max_attempts=min(max_retries, 4),
            backoff_days=base_backoff[:4] or [2, 3, 5, 7],
            escalate_after=4, escalation_target="credit_control",
            summary="Soft decline — retry on a payday-aligned cadence before any human touch.",
            tone_ladder=[MessageTone.FRIENDLY_REMINDER, MessageTone.FRIENDLY_REMINDER,
                         MessageTone.FIRM_REMINDER, MessageTone.URGENT],
        )

    if code is FailureCode.PROCESSING_ERROR:
        # Transient/network. Retry fast and quietly; rarely needs the customer.
        return Playbook(
            code, recoverable=True, needs_customer_action=False,
            max_attempts=min(max_retries, 3), backoff_days=[0, 1, 2],
            escalate_after=3, escalation_target="human_review",
            summary="Transient processor error — fast quiet retries, no dunning unless it persists.",
            tone_ladder=[MessageTone.FRIENDLY_REMINDER, MessageTone.FIRM_REMINDER],
        )

    if code is FailureCode.AUTHENTICATION_REQUIRED:
        # 3DS — needs the customer to re-authenticate, then retry succeeds.
        return Playbook(
            code, recoverable=True, needs_customer_action=True,
            max_attempts=min(max_retries, 3), backoff_days=[1, 2, 4],
            escalate_after=3, escalation_target="human_review",
            summary="Bank wants 3-D Secure — prompt the customer to confirm, then retry.",
            tone_ladder=[MessageTone.FRIENDLY_REMINDER, MessageTone.FIRM_REMINDER,
                         MessageTone.URGENT],
        )

    if code is FailureCode.DO_NOT_HONOR:
        # Ambiguous issuer block. A couple of spaced retries, then escalate.
        return Playbook(
            code, recoverable=True, needs_customer_action=True,
            max_attempts=2, backoff_days=[2, 5],
            escalate_after=2, escalation_target="credit_control",
            summary="Issuer 'do not honor' — limited retries, ask the customer to call their bank.",
            tone_ladder=[MessageTone.FIRM_REMINDER, MessageTone.URGENT],
        )

    if code is FailureCode.CARD_DECLINED:
        return Playbook(
            code, recoverable=True, needs_customer_action=True,
            max_attempts=2, backoff_days=[2, 4],
            escalate_after=2, escalation_target="credit_control",
            summary="Generic decline — one retry, then ask for an updated card.",
            tone_ladder=[MessageTone.FIRM_REMINDER, MessageTone.URGENT],
        )

    if code is FailureCode.EXPIRED_CARD:
        # Hard decline. Retrying the same card can't work — message-led.
        return Playbook(
            code, recoverable=False, needs_customer_action=True,
            max_attempts=1, backoff_days=[3],
            escalate_after=2, escalation_target="credit_control",
            summary="Card expired — no point retrying; drive the customer to update payment details.",
            tone_ladder=[MessageTone.FRIENDLY_REMINDER, MessageTone.FIRM_REMINDER,
                         MessageTone.URGENT],
        )

    if code is FailureCode.LOST_OR_STOLEN:
        # Never retry a reported card. Require a new method, escalate.
        return Playbook(
            code, recoverable=False, needs_customer_action=True,
            max_attempts=0, backoff_days=[],
            escalate_after=1, escalation_target="credit_control",
            summary="Card reported lost/stolen — do not retry; require a new payment method.",
            tone_ladder=[MessageTone.URGENT],
        )

    # FRAUD_SUSPECTED
    return Playbook(
        code, recoverable=False, needs_customer_action=True,
        max_attempts=0, backoff_days=[],
        escalate_after=0, escalation_target="human_review",
        summary="Suspected fraud — halt automation and route to a human immediately.",
        tone_ladder=[],
    )
