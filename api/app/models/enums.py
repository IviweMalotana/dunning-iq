"""Domain enums shared across models, schemas, and the agent.

Stored as portable VARCHARs (``native_enum=False``) so the same migrations run
against SQLite (local) and Postgres (prod) without provider-specific ENUM types.
"""

from __future__ import annotations

import enum


class PaymentStatus(enum.StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"


class FailureCode(enum.StrEnum):
    """Normalised decline reasons (mapped from Stripe/Paddle codes)."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    DO_NOT_HONOR = "do_not_honor"
    CARD_DECLINED = "card_declined"
    LOST_OR_STOLEN = "lost_or_stolen_card"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PROCESSING_ERROR = "processing_error"
    FRAUD_SUSPECTED = "fraud_suspected"

    @property
    def label(self) -> str:
        return {
            "insufficient_funds": "Insufficient funds",
            "expired_card": "Expired card",
            "do_not_honor": "Do not honor",
            "card_declined": "Card declined",
            "lost_or_stolen_card": "Lost or stolen card",
            "authentication_required": "Authentication required",
            "processing_error": "Technical / processing error",
            "fraud_suspected": "Suspected fraud",
        }[self.value]

    @property
    def is_recoverable(self) -> bool:
        """Soft declines are worth retrying; hard declines need the customer."""
        return self in {
            FailureCode.INSUFFICIENT_FUNDS,
            FailureCode.PROCESSING_ERROR,
            FailureCode.DO_NOT_HONOR,
            FailureCode.AUTHENTICATION_REQUIRED,
        }


class CaseStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    WRITTEN_OFF = "written_off"
    PAUSED = "paused"

    @property
    def is_open(self) -> bool:
        return self in {CaseStatus.IN_PROGRESS, CaseStatus.ESCALATED, CaseStatus.PAUSED}


class EventType(enum.StrEnum):
    CASE_OPENED = "case_opened"
    CLASSIFICATION = "classification"
    RETRY_SCHEDULED = "retry_scheduled"
    RETRY_ATTEMPTED = "retry_attempted"
    RETRY_SUCCEEDED = "retry_succeeded"
    RETRY_FAILED = "retry_failed"
    MESSAGE_DRAFTED = "message_drafted"
    MESSAGE_SENT = "message_sent"
    ESCALATED = "escalated"
    HUMAN_REVIEW = "human_review"
    RESOLVED = "resolved"
    WRITTEN_OFF = "written_off"
    NOTE = "note"


class Actor(enum.StrEnum):
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class MessageChannel(enum.StrEnum):
    EMAIL = "email"
    SMS = "sms"


class MessageTone(enum.StrEnum):
    """Escalation ladder for customer comms."""

    FRIENDLY_REMINDER = "friendly_reminder"
    FIRM_REMINDER = "firm_reminder"
    URGENT = "urgent"
    FINAL_NOTICE = "final_notice"
    CREDIT_CONTROL = "credit_control"

    @property
    def label(self) -> str:
        return {
            "friendly_reminder": "Friendly reminder",
            "firm_reminder": "Firm reminder",
            "urgent": "Urgent",
            "final_notice": "Final notice",
            "credit_control": "Credit control hand-off",
        }[self.value]


class MessageStatus(enum.StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    EDITED = "edited"


class SubscriptionStatus(enum.StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
