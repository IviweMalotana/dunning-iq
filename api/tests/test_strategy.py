"""Invariants for the recovery playbooks — the agent's hard guardrails."""

from app.agent.strategy import playbook_for
from app.models.enums import FailureCode

POLICY = {"max_retries": 4, "backoff_days": [2, 3, 5, 7]}


def pb(code: FailureCode):
    return playbook_for(code, **POLICY)


def test_fraud_never_retries_and_routes_to_human():
    p = pb(FailureCode.FRAUD_SUSPECTED)
    assert p.max_attempts == 0
    assert p.escalation_target == "human_review"
    assert p.recoverable is False


def test_lost_or_stolen_never_retries():
    assert pb(FailureCode.LOST_OR_STOLEN).max_attempts == 0


def test_expired_card_is_not_retried_in_bulk():
    p = pb(FailureCode.EXPIRED_CARD)
    assert p.recoverable is False
    assert p.needs_customer_action is True
    assert p.max_attempts <= 1


def test_insufficient_funds_is_the_most_retryable():
    p = pb(FailureCode.INSUFFICIENT_FUNDS)
    assert p.recoverable is True
    assert p.needs_customer_action is False
    assert p.max_attempts == 4
    assert len(p.backoff_days) == p.max_attempts


def test_processing_error_retries_fast():
    p = pb(FailureCode.PROCESSING_ERROR)
    assert p.backoff_days[0] == 0  # retry immediately
    assert p.recoverable is True


def test_every_failure_code_has_a_playbook():
    for code in FailureCode:
        p = pb(code)
        assert p.summary
        # Tone ladder must cover every retry step we might message on.
        for step in range(1, p.max_attempts + 1):
            assert p.tone_for_step(step) is not None
