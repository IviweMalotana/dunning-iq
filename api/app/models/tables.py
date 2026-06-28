"""SQLAlchemy ORM models for Dunning IQ.

Portable across SQLite (local) and Postgres (prod): string UUID PKs, integer
minor-unit money, ``JSON`` columns, and VARCHAR-backed enums.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import (
    Actor,
    CaseStatus,
    EventType,
    FailureCode,
    MessageChannel,
    MessageStatus,
    MessageTone,
    PaymentStatus,
    SubscriptionStatus,
)


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


def _enum(py_enum: type, name: str) -> Enum:
    """VARCHAR-backed enum that stores the value (not the member name)."""
    return Enum(
        py_enum,
        native_enum=False,
        length=40,
        values_callable=lambda e: [m.value for m in e],
        name=name,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), index=True)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    segment: Mapped[str] = mapped_column(String(24), default="growth")  # starter|growth|enterprise
    country: Mapped[str] = mapped_column(String(2), default="US")

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    cases: Mapped[list[DunningCase]] = relationship(back_populates="customer")


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    plan_name: Mapped[str] = mapped_column(String(80))
    amount_minor: Mapped[int] = mapped_column(Integer)  # recurring charge, minor units
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    interval: Mapped[str] = mapped_column(String(12), default="month")  # month|year
    status: Mapped[SubscriptionStatus] = mapped_column(
        _enum(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.ACTIVE,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped[Customer] = relationship(back_populates="subscriptions")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True, index=True
    )
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus, "payment_status"), index=True)
    failure_code: Mapped[FailureCode | None] = mapped_column(
        _enum(FailureCode, "failure_code"), nullable=True, index=True
    )
    failure_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    processor: Mapped[str] = mapped_column(String(16), default="stripe")  # stripe|paddle
    case_id: Mapped[str | None] = mapped_column(
        ForeignKey("dunning_cases.id"), nullable=True, index=True
    )

    customer: Mapped[Customer] = relationship()
    subscription: Mapped[Subscription | None] = relationship()


class DunningCase(Base, TimestampMixin):
    __tablename__ = "dunning_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True
    )
    triggering_payment_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[CaseStatus] = mapped_column(
        _enum(CaseStatus, "case_status"), default=CaseStatus.IN_PROGRESS, index=True
    )
    failure_code: Mapped[FailureCode] = mapped_column(_enum(FailureCode, "case_failure_code"))
    amount_at_risk_minor: Mapped[int] = mapped_column(Integer)
    recovered_amount_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Agent plan + progress
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalated_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="cases")
    subscription: Mapped[Subscription | None] = relationship()
    events: Mapped[list[DunningEvent]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="DunningEvent.occurred_at",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class DunningEvent(Base):
    __tablename__ = "dunning_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("dunning_cases.id"), index=True)
    type: Mapped[EventType] = mapped_column(_enum(EventType, "event_type"), index=True)
    actor: Mapped[Actor] = mapped_column(_enum(Actor, "event_actor"), default=Actor.AGENT)
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    title: Mapped[str] = mapped_column(String(140))
    # The agent's plain-English justification — the audit trail, the selling point.
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    payment_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

    case: Mapped[DunningCase] = relationship(back_populates="events")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("dunning_cases.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)

    channel: Mapped[MessageChannel] = mapped_column(
        _enum(MessageChannel, "message_channel"), default=MessageChannel.EMAIL
    )
    tone: Mapped[MessageTone] = mapped_column(_enum(MessageTone, "message_tone"))
    status: Mapped[MessageStatus] = mapped_column(
        _enum(MessageStatus, "message_status"), default=MessageStatus.DRAFT
    )
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(48), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[DunningCase] = relationship(back_populates="messages")


class Policy(Base, TimestampMixin):
    """Editable retry policy + message tone settings (a single active row).

    The settings editor (M5) mutates this; the agent reads it when planning.
    """

    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(60), default="Default policy")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    max_retries: Mapped[int] = mapped_column(Integer, default=4)
    backoff_days: Mapped[list] = mapped_column(JSON, default=lambda: [1, 3, 5, 7])
    retry_window_days: Mapped[int] = mapped_column(Integer, default=21)
    escalate_after_step: Mapped[int] = mapped_column(Integer, default=4)
    base_tone: Mapped[str] = mapped_column(String(40), default="friendly_reminder")
    brand_voice: Mapped[str] = mapped_column(
        String(400),
        default="Warm, concise, and respectful. We assume good faith and make it "
        "effortless to fix the payment.",
    )
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)  # human-in-the-loop by default
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
