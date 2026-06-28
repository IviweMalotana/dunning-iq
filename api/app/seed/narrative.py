"""Deterministic 'replay' generator for agent reasoning and customer messages.

This is what ships in the seeded demo so it's fully clickable with no API key.
The live Claude engine (M3) produces the same shapes; this stays as the offline
fallback. Copy here is real dunning prose — no placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.strategy import Playbook
from app.models.enums import FailureCode, MessageTone

BRAND = "Northwind"  # demo brand name (not a real company)
UPDATE_LINK = "https://billing.northwind.example/update"


@dataclass
class CaseContext:
    first_name: str
    full_name: str
    company: str | None
    amount_minor: int
    currency: str
    plan_name: str
    failure_code: FailureCode
    attempt_number: int = 1

    @property
    def amount(self) -> str:
        return money(self.amount_minor, self.currency)

    @property
    def who(self) -> str:
        return f"{self.full_name}" + (f" ({self.company})" if self.company else "")


def money(minor: int, currency: str = "USD") -> str:
    symbol = {"USD": "$", "GBP": "£", "EUR": "€", "AUD": "A$", "CAD": "C$"}.get(currency, "")
    return f"{symbol}{minor / 100:,.2f}"


# Short customer-facing hint per failure code.
_ACTION_HINT = {
    FailureCode.INSUFFICIENT_FUNDS: "We'll retry automatically, or you can use a different card.",
    FailureCode.EXPIRED_CARD: "The card on file has expired — please add a current one.",
    FailureCode.DO_NOT_HONOR: "Your bank declined the charge; a quick call to them usually clears it.",
    FailureCode.CARD_DECLINED: "Please check the card details or try another payment method.",
    FailureCode.LOST_OR_STOLEN: "This card can no longer be charged — please add a new one.",
    FailureCode.AUTHENTICATION_REQUIRED: "Your bank needs you to confirm this payment (3-D Secure).",
    FailureCode.PROCESSING_ERROR: "This looked like a temporary glitch — we'll try again shortly.",
    FailureCode.FRAUD_SUSPECTED: "For your security, please confirm this charge with our team.",
}


# ── Agent reasoning ──────────────────────────────────────────────────────────

def classification_reasoning(ctx: CaseContext, pb: Playbook) -> str:
    code = ctx.failure_code
    kind = "soft" if pb.recoverable and not pb.needs_customer_action else (
        "customer-action" if pb.needs_customer_action and pb.recoverable else "hard"
    )
    lead = {
        FailureCode.INSUFFICIENT_FUNDS:
            "Processor returned `insufficient_funds`. This is the single most recoverable "
            "decline — the card is valid, the account is simply short right now.",
        FailureCode.EXPIRED_CARD:
            "Processor returned `expired_card`. The card itself is dead; no retry against it "
            "can ever succeed, so this is fundamentally a 'get new details' problem.",
        FailureCode.DO_NOT_HONOR:
            "Processor returned `do_not_honor`. This is an opaque issuer block — it can clear "
            "on its own or signal a deeper hold, so I treat it as recoverable but low-confidence.",
        FailureCode.CARD_DECLINED:
            "Processor returned a generic `card_declined`. Cause is ambiguous; one retry is "
            "cheap insurance, but I won't lean on automation here.",
        FailureCode.LOST_OR_STOLEN:
            "Processor flagged the card as lost or stolen. Retrying would be pointless and "
            "could look like card-testing — the card must be replaced.",
        FailureCode.AUTHENTICATION_REQUIRED:
            "Processor returned `authentication_required` (3-D Secure). The money is likely "
            "there; the bank just wants the customer to confirm the charge.",
        FailureCode.PROCESSING_ERROR:
            "Processor returned a `processing_error`. This reads as transient — a gateway or "
            "network hiccup rather than anything wrong with the card.",
        FailureCode.FRAUD_SUSPECTED:
            "Processor flagged the charge as fraudulent. Automation stops here — anything else "
            "risks the customer and our processor standing.",
    }[code]
    return (
        f"{lead} Classified as **{code.label}** ({kind} decline) on a {ctx.amount} charge for "
        f"{ctx.who}. Strategy: {pb.summary}"
    )


def strategy_reasoning(ctx: CaseContext, pb: Playbook) -> str:
    if pb.max_attempts == 0:
        return (
            f"No automated retries scheduled — retrying a {ctx.failure_code.label.lower()} would "
            f"waste processor fees and can't succeed. Routing straight to "
            f"{_target_phrase(pb.escalation_target)} with a request for new payment details."
        )
    cadence = ", ".join(f"+{d}d" if d else "now" for d in pb.backoff_days[: pb.max_attempts])
    extra = ""
    if ctx.failure_code is FailureCode.INSUFFICIENT_FUNDS:
        extra = (" The widening gaps deliberately straddle a likely pay date — hitting the card "
                 "again the morning after payday is where most of these recover.")
    elif ctx.failure_code is FailureCode.PROCESSING_ERROR:
        extra = " Tight spacing because transient errors usually clear within hours."
    elif ctx.failure_code is FailureCode.AUTHENTICATION_REQUIRED:
        extra = " Each retry is gated behind the customer completing 3-D Secure first."
    return (
        f"Scheduling up to {pb.max_attempts} retr{'y' if pb.max_attempts == 1 else 'ies'} "
        f"({cadence}). If still unpaid after step {pb.escalate_after}, escalate to "
        f"{_target_phrase(pb.escalation_target)}.{extra}"
    )


def retry_reasoning(ctx: CaseContext, step: int, succeeded: bool) -> str:
    if succeeded:
        return (
            f"Retry #{step} cleared — {ctx.amount} captured. The card was good all along; the "
            f"timing fixed it. Closing the case as recovered and standing down the dunning ladder."
        )
    return (
        f"Retry #{step} failed with the same {ctx.failure_code.label.lower()} response. Moving to "
        f"the next scheduled attempt and stepping the customer message up a tone."
    )


def message_reasoning(ctx: CaseContext, tone: MessageTone, step: int) -> str:
    return (
        f"Drafting a **{tone.label.lower()}** at step {step}. Tone is calibrated to where we are "
        f"in the ladder: firm enough to prompt action, never punitive. Leading with the fix "
        f"({_ACTION_HINT[ctx.failure_code].lower()}) rather than the failure."
    )


def escalation_reasoning(ctx: CaseContext, pb: Playbook) -> str:
    return (
        f"Automated recovery is exhausted for this {ctx.failure_code.label.lower()} case "
        f"({ctx.amount} at risk). Handing off to {_target_phrase(pb.escalation_target)} with the "
        f"full decision history attached so a human picks up with full context, not a cold start."
    )


def resolution_reasoning(ctx: CaseContext, step: int) -> str:
    return (
        f"Payment recovered at step {step}. {ctx.amount} captured and the subscription is back to "
        f"active. Net outcome: revenue saved with zero human time spent on this account."
    )


def writeoff_reasoning(ctx: CaseContext) -> str:
    return (
        f"After the full ladder with no recovery and no customer response, marking {ctx.amount} as "
        f"written off and cancelling the subscription. Logged so finance can reconcile and so we "
        f"learn which decline types convert least."
    )


def _target_phrase(target: str | None) -> str:
    return {
        "credit_control": "credit control",
        "human_review": "a human reviewer",
    }.get(target or "", "a human")


# ── Customer messages ────────────────────────────────────────────────────────

def draft_message(ctx: CaseContext, tone: MessageTone, next_date: str | None) -> tuple[str, str]:
    """Return (subject, body) for a dunning email at the given tone."""
    first = ctx.first_name
    hint = _ACTION_HINT[ctx.failure_code]
    retry_line = (
        f"We'll automatically try again on {next_date}. " if next_date else ""
    )

    if tone is MessageTone.FRIENDLY_REMINDER:
        subject = f"A quick note about your {ctx.plan_name} payment"
        body = (
            f"Hi {first},\n\n"
            f"We tried to process your {ctx.amount} payment for {ctx.plan_name} today and it "
            f"didn't go through. {hint}\n\n"
            f"{retry_line}If it's easier, you can update your payment details here:\n{UPDATE_LINK}\n\n"
            f"No need to worry — these things happen, and your account is fully active in the "
            f"meantime.\n\nThanks for being with us,\nThe {BRAND} Billing Team"
        )
    elif tone is MessageTone.FIRM_REMINDER:
        subject = f"Action needed: your {ctx.plan_name} payment didn't go through"
        body = (
            f"Hi {first},\n\n"
            f"We've now tried your {ctx.amount} payment for {ctx.plan_name} a couple of times "
            f"without success. {hint}\n\n"
            f"To keep your subscription running, please update your payment method:\n{UPDATE_LINK}\n\n"
            f"{retry_line}If anything's unclear, just reply to this email and we'll help.\n\n"
            f"Best,\nThe {BRAND} Billing Team"
        )
    elif tone is MessageTone.URGENT:
        subject = f"Your {ctx.plan_name} subscription is at risk"
        body = (
            f"Hi {first},\n\n"
            f"We still haven't been able to collect your {ctx.amount} payment for "
            f"{ctx.plan_name}. {hint}\n\n"
            f"Please update your payment details in the next few days to avoid any interruption "
            f"to your service:\n{UPDATE_LINK}\n\n"
            f"We'd hate to see your account paused over something this quick to fix.\n\n"
            f"The {BRAND} Billing Team"
        )
    elif tone is MessageTone.FINAL_NOTICE:
        subject = f"Final notice before your {ctx.plan_name} account is paused"
        body = (
            f"Hi {first},\n\n"
            f"Despite several attempts, your {ctx.amount} payment for {ctx.plan_name} remains "
            f"outstanding. This is a final reminder before we pause your account.\n\n"
            f"You can settle it in under a minute here:\n{UPDATE_LINK}\n\n"
            f"If there's a problem we can help with, please reply today and we'll work something "
            f"out.\n\nThe {BRAND} Billing Team"
        )
    else:  # CREDIT_CONTROL
        subject = f"Regarding the outstanding balance on your {BRAND} account"
        body = (
            f"Hello {ctx.full_name},\n\n"
            f"Our records show an outstanding balance of {ctx.amount} on your {ctx.plan_name} "
            f"subscription that we've been unable to collect.\n\n"
            f"We'd like to resolve this with you directly. Please settle the balance here:\n"
            f"{UPDATE_LINK}\n\nor reply to arrange a payment plan. If we don't hear from you, the "
            f"account will be referred for formal collection.\n\n"
            f"Regards,\n{BRAND} Credit Control"
        )
    return subject, body
