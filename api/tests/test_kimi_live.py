"""Live-path Kimi tests with a mocked OpenAI client.

These exercise the *actual* code that runs when a key is present — prompt
construction, JSON parsing, schema validation, fence stripping, cache write,
and Decision assembly — without making a network call.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.agent.llm import LiveKimiEngine, _ReasoningOnly, _ReasoningWithMessage
from app.agent.strategy import playbook_for
from app.models.enums import FailureCode, MessageTone
from app.seed.narrative import CaseContext

POLICY = {"max_retries": 4, "backoff_days": [2, 3, 5, 7]}


def _ctx(code: FailureCode = FailureCode.INSUFFICIENT_FUNDS) -> CaseContext:
    return CaseContext(
        first_name="Sam", full_name="Sam Rivera", company="Atlas Labs",
        amount_minor=9900, currency="USD", plan_name="Growth (monthly)", failure_code=code,
    )


def _moonshot_response(content: str) -> SimpleNamespace:
    """Build a fake ChatCompletion shaped like openai SDK v2 would return it."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _patch_engine(monkeypatch, engine: LiveKimiEngine, content: str) -> MagicMock:
    """Wire a mocked OpenAI client onto the engine and pre-stub config."""
    from app.core import config

    monkeypatch.setattr(config.settings, "moonshot_api_key", "test-key")
    monkeypatch.setattr(config.settings, "llm_provider", "kimi")
    # Bypass cache so we test the live path, not the cache hit.
    engine._cache = {}
    engine._save = lambda *a, **kw: None  # no-op
    mock_client = MagicMock()
    mock_client.chat.completions.create = MagicMock(return_value=_moonshot_response(content))
    engine._client = mock_client
    return mock_client


# Realistic Kimi payload — what Moonshot returns for a reasoning+message prompt.
_KIMI_GOOD_JSON = json.dumps({
    "confidence": 0.94,
    "classification_reasoning": (
        "Processor returned insufficient_funds — the card is valid but the "
        "account is short. This is the most recoverable decline class."
    ),
    "strategy_reasoning": (
        "Scheduling four retries (+2d, +3d, +5d, +7d). The widening cadence "
        "straddles a likely pay date; after step 4 we hand off to credit control."
    ),
    "message_subject": "A quick note about your Growth (monthly) payment",
    "message_body": "Hi Sam,\n\nWe'll retry your $99.00 payment soon. No action needed.",
    "message_reasoning": (
        "Friendly reminder at step 1 — leads with the fix, never punitive."
    ),
})


def test_kimi_live_call_produces_decision(monkeypatch):
    engine = LiveKimiEngine()
    client = _patch_engine(monkeypatch, engine, _KIMI_GOOD_JSON)
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")

    assert d.source == "kimi"
    assert d.confidence == pytest.approx(0.94)
    assert "insufficient_funds" in d.classification_reasoning
    assert d.message_subject and d.message_body and d.message_reasoning

    # The SDK was called with the right shape.
    client.chat.completions.create.assert_called_once()
    call = client.chat.completions.create.call_args
    assert call.kwargs["model"] == "kimi-k2-0711-preview"
    assert call.kwargs["response_format"] == {"type": "json_object"}
    msgs = call.kwargs["messages"]
    assert msgs[0]["role"] == "system" and "Dunning IQ" in msgs[0]["content"]
    # The schema is inlined in the user prompt so Kimi knows the shape.
    assert "message_subject" in msgs[1]["content"]
    assert "Growth (monthly)" in msgs[1]["content"]


def test_kimi_strips_markdown_fences(monkeypatch):
    """Kimi sometimes wraps JSON in ```json fences even with response_format set."""
    engine = LiveKimiEngine()
    _patch_engine(monkeypatch, engine, f"```json\n{_KIMI_GOOD_JSON}\n```")
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")
    assert d.source == "kimi"
    assert d.message_subject  # fully parsed despite the fences


def test_kimi_bare_backticks_also_stripped(monkeypatch):
    engine = LiveKimiEngine()
    _patch_engine(monkeypatch, engine, f"```\n{_KIMI_GOOD_JSON}\n```")
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")
    assert d.source == "kimi"


def test_kimi_invalid_json_falls_back_gracefully(monkeypatch):
    engine = LiveKimiEngine()
    _patch_engine(monkeypatch, engine, "this is not json at all, sorry")
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")
    # Garbage in → deterministic fallback, honestly labelled.
    assert d.source == "replay"
    assert d.message_body  # the deterministic engine still drafts something


def test_kimi_schema_mismatch_falls_back(monkeypatch):
    """Valid JSON but missing required fields → schema validation fails → fallback."""
    engine = LiveKimiEngine()
    _patch_engine(monkeypatch, engine, json.dumps({"confidence": 0.9}))  # missing reasoning
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")
    assert d.source == "replay"


def test_kimi_empty_response_falls_back(monkeypatch):
    engine = LiveKimiEngine()
    _patch_engine(monkeypatch, engine, "")
    pb = playbook_for(FailureCode.INSUFFICIENT_FUNDS, **POLICY)

    d = engine.analyze(_ctx(), pb, tone=MessageTone.FRIENDLY_REMINDER, next_date="Jul 2")
    assert d.source == "replay"


def test_kimi_no_message_path_uses_reasoning_only_schema(monkeypatch):
    """Hard declines (fraud, lost card) ask for reasoning only — no message fields."""
    engine = LiveKimiEngine()
    payload = json.dumps({
        "confidence": 0.97,
        "classification_reasoning": "Processor flagged fraudulent — halt automation.",
        "strategy_reasoning": "No retries; route immediately to a human reviewer.",
    })
    client = _patch_engine(monkeypatch, engine, payload)
    pb = playbook_for(FailureCode.FRAUD_SUSPECTED, **POLICY)

    d = engine.analyze(_ctx(FailureCode.FRAUD_SUSPECTED), pb)  # no tone

    assert d.source == "kimi"
    assert d.message_subject is None
    # And the prompt we sent didn't ask for a message either.
    prompt = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Draft the first customer email" not in prompt


def test_schemas_match_what_we_validate_against():
    """Lock the schema field names so a rename doesn't silently break Kimi parsing."""
    bare = _ReasoningOnly.model_fields.keys()
    full = _ReasoningWithMessage.model_fields.keys()
    assert set(bare) == {"confidence", "classification_reasoning", "strategy_reasoning"}
    assert set(full) - set(bare) == {"message_subject", "message_body", "message_reasoning"}
