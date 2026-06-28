"""Inbound payment webhook envelope (Stripe/Paddle-shaped) and decline mapping.

This is a normalised envelope — the fields a real `invoice.payment_failed` from
Stripe or a `transaction.payment_failed` from Paddle carry once you strip the
provider-specific object graph. The ingest layer maps raw processor decline
codes onto our internal :class:`FailureCode`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import FailureCode

EventType = Literal["payment_failed", "payment_succeeded"]


class CustomerPayload(BaseModel):
    external_id: str = Field(examples=["cus_9f2a1bc7d4"])
    email: str
    name: str
    company: str | None = None
    country: str = "US"


class SubscriptionPayload(BaseModel):
    external_id: str = Field(examples=["sub_7c1a93de20"])
    plan_name: str
    amount_minor: int = Field(gt=0, description="Recurring charge in minor units (cents)")
    currency: str = "USD"
    interval: Literal["month", "year"] = "month"


class PaymentPayload(BaseModel):
    external_id: str = Field(examples=["pay_3a8f10c2bb"])
    amount_minor: int = Field(gt=0)
    currency: str = "USD"
    processor: Literal["stripe", "paddle"] = "stripe"
    # Present on failures; mapped via RAW_DECLINE_MAP if a raw processor code.
    failure_code: str | None = None
    failure_message: str | None = None


class EventData(BaseModel):
    customer: CustomerPayload
    subscription: SubscriptionPayload
    payment: PaymentPayload


class PaymentWebhookEvent(BaseModel):
    id: str = Field(examples=["evt_a1b2c3d4e5"])
    type: EventType
    created: int | None = Field(default=None, description="Unix timestamp from the processor")
    data: EventData


class IngestResult(BaseModel):
    event_id: str
    event_type: EventType
    customer_id: str
    payment_id: str
    case_id: str | None = None
    case_status: str | None = None
    action: str
    detail: str


# Raw Stripe/Paddle decline codes → normalised FailureCode.
RAW_DECLINE_MAP: dict[str, FailureCode] = {
    # Stripe `decline_code` / charge failure codes
    "insufficient_funds": FailureCode.INSUFFICIENT_FUNDS,
    "expired_card": FailureCode.EXPIRED_CARD,
    "do_not_honor": FailureCode.DO_NOT_HONOR,
    "card_declined": FailureCode.CARD_DECLINED,
    "generic_decline": FailureCode.CARD_DECLINED,
    "lost_card": FailureCode.LOST_OR_STOLEN,
    "stolen_card": FailureCode.LOST_OR_STOLEN,
    "pickup_card": FailureCode.LOST_OR_STOLEN,
    "authentication_required": FailureCode.AUTHENTICATION_REQUIRED,
    "processing_error": FailureCode.PROCESSING_ERROR,
    "try_again_later": FailureCode.PROCESSING_ERROR,
    "issuer_not_available": FailureCode.PROCESSING_ERROR,
    "fraudulent": FailureCode.FRAUD_SUSPECTED,
    "merchant_blacklist": FailureCode.FRAUD_SUSPECTED,
    # Paddle-style
    "insufficient_balance": FailureCode.INSUFFICIENT_FUNDS,
    "card_expired": FailureCode.EXPIRED_CARD,
    "declined": FailureCode.CARD_DECLINED,
    "fraud": FailureCode.FRAUD_SUSPECTED,
}


def normalise_failure_code(raw: str | None) -> FailureCode:
    """Map a raw processor decline code to a FailureCode (default: card_declined)."""
    if not raw:
        return FailureCode.CARD_DECLINED
    key = raw.strip().lower()
    if key in RAW_DECLINE_MAP:
        return RAW_DECLINE_MAP[key]
    # Already one of our normalised values?
    try:
        return FailureCode(key)
    except ValueError:
        return FailureCode.CARD_DECLINED
