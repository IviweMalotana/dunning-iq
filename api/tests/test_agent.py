"""Decision-engine + live-fallback tests (no API key needed)."""

from app.agent.engine import DecisionEngine, get_engine
from app.agent.llm import LiveClaudeEngine, LiveKimiEngine
from app.agent.strategy import playbook_for
from app.models.enums import FailureCode, MessageTone
from app.seed.narrative import CaseContext

POLICY = {"max_retries": 4, "backoff_days": [2, 3, 5, 7]}


def _ctx(code: FailureCode) -> CaseContext:
    return CaseContext(
        first_name="Sam", full_name="Sam Rivera", company="Atlas Labs",
        amount_minor=9900, currency="USD", plan_name="Growth (monthly)", failure_code=code,
    )


def test_analyze_drafts_message_when_tone_given():
    code = FailureCode.INSUFFICIENT_FUNDS
    pb = playbook_for(code, **POLICY)
    d = DecisionEngine().analyze(_ctx(code), pb, tone=MessageTone.FRIENDLY_REMINDER,
                                 next_date="Jul 2")
    assert d.source == "replay"
    assert 0 <= d.confidence <= 1
    assert d.classification_reasoning and d.strategy_reasoning
    assert d.message_subject and d.message_body and d.message_reasoning


def test_analyze_skips_message_for_escalate_now():
    code = FailureCode.FRAUD_SUSPECTED
    pb = playbook_for(code, **POLICY)
    d = DecisionEngine().analyze(_ctx(code), pb)  # no tone — fraud doesn't message
    assert d.message_subject is None
    assert d.classification_reasoning  # but reasoning is still produced


def test_kimi_engine_falls_back_without_key(monkeypatch):
    """No MOONSHOT_API_KEY → live call fails → deterministic fallback, honestly labelled."""
    from app.core import config

    monkeypatch.setattr(config.settings, "moonshot_api_key", None)
    code = FailureCode.EXPIRED_CARD
    pb = playbook_for(code, **POLICY)
    d = LiveKimiEngine().analyze(_ctx(code), pb, tone=MessageTone.FRIENDLY_REMINDER,
                                 next_date="Jul 2")
    assert d.source == "replay"
    assert d.classification_reasoning
    assert d.message_body


def test_claude_engine_falls_back_without_key(monkeypatch):
    """Claude path still works as the alternative provider."""
    from app.core import config

    monkeypatch.setattr(config.settings, "anthropic_api_key", None)
    code = FailureCode.EXPIRED_CARD
    pb = playbook_for(code, **POLICY)
    d = LiveClaudeEngine().analyze(_ctx(code), pb, tone=MessageTone.FRIENDLY_REMINDER,
                                   next_date="Jul 2")
    assert d.source == "replay"


def test_get_engine_dispatches_by_provider(monkeypatch):
    from app.core import config

    # Default: kimi keyed → Kimi engine
    monkeypatch.setattr(config.settings, "llm_provider", "kimi")
    monkeypatch.setattr(config.settings, "moonshot_api_key", "test-key")
    monkeypatch.setattr(config.settings, "anthropic_api_key", None)
    assert isinstance(get_engine(), LiveKimiEngine)

    # Switch to claude
    monkeypatch.setattr(config.settings, "llm_provider", "claude")
    monkeypatch.setattr(config.settings, "moonshot_api_key", None)
    monkeypatch.setattr(config.settings, "anthropic_api_key", "test-key")
    assert isinstance(get_engine(), LiveClaudeEngine)

    # No key for the active provider → deterministic
    monkeypatch.setattr(config.settings, "anthropic_api_key", None)
    monkeypatch.setattr(config.settings, "moonshot_api_key", None)
    engine = get_engine()
    assert isinstance(engine, DecisionEngine)
    assert not isinstance(engine, (LiveKimiEngine, LiveClaudeEngine))
