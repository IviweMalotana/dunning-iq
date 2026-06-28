"""Run the decision engine on a sample failure and print the agent's reasoning.

    uv run python -m app.agent.demo                 # default: insufficient_funds
    uv run python -m app.agent.demo expired_card

Shows whether the live Claude engine (ANTHROPIC_API_KEY set) or the deterministic
fallback produced the decision — handy for confirming your key works end to end.
"""

from __future__ import annotations

import sys

from app.agent.engine import get_engine
from app.agent.strategy import playbook_for
from app.core.config import settings
from app.models.enums import FailureCode
from app.seed.narrative import CaseContext


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else "insufficient_funds"
    try:
        code = FailureCode(raw)
    except ValueError:
        print(f"Unknown failure code '{raw}'. Options: {', '.join(c.value for c in FailureCode)}")
        sys.exit(1)

    ctx = CaseContext(
        first_name="Jordan", full_name="Jordan Mensah", company="Cedar Analytics",
        amount_minor=24900, currency="USD", plan_name="Scale (monthly)", failure_code=code,
    )
    pb = playbook_for(code, max_retries=4, backoff_days=[2, 3, 5, 7])
    tone = pb.tone_for_step(1) if pb.max_attempts else None

    engine = get_engine()
    print(f"Engine: {'LIVE (Claude)' if settings.agent_live_enabled else 'deterministic (no key)'}")
    print(f"Failure: {code.label}  |  Amount: {ctx.amount}  |  Customer: {ctx.who}\n")

    decision = engine.analyze(ctx, pb, tone=tone, next_date="Jul 2",
                              brand_voice="Warm, concise, and respectful.")

    print(f"── Decided by: {decision.source}  (confidence {decision.confidence:.0%})")
    print("\n[Classification]\n" + decision.classification_reasoning)
    print("\n[Strategy]\n" + decision.strategy_reasoning)
    if decision.message_subject:
        print("\n[Drafted message]")
        print("Subject:", decision.message_subject)
        print(decision.message_body)
        print("\n[Why this message]\n" + (decision.message_reasoning or ""))


if __name__ == "__main__":
    main()
