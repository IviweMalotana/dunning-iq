"""Live LLM-powered decision engine.

Produces the agent's classification, retry-strategy rationale, and the drafted
customer message via a single LLM call with structured output. The billing
guardrails in ``strategy.py`` still bound what the agent can do — the LLM
supplies the plain-English *reasoning* and the customer *prose*, which is the
auditable, human-readable layer the product sells on.

Two providers are supported behind the same ``LiveLLMEngine`` base:

* :class:`LiveKimiEngine` — Moonshot AI's Kimi (default), via the OpenAI-compatible
  Chat Completions API with JSON-mode + Pydantic validation.
* :class:`LiveClaudeEngine` — Anthropic Claude via the official SDK with
  ``messages.parse`` and a Pydantic schema.

Resilience: any API error (missing key, rate limit, malformed output) falls back
to the deterministic base engine, so a webhook is never dropped. Successful
generations are cached to disk so re-seeding or re-processing is free and
offline. The cache key includes the model id, so flipping providers does not
return stale text.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.agent.engine import Decision, DecisionEngine
from app.agent.strategy import Playbook
from app.core.config import settings
from app.models.enums import MessageTone
from app.seed.narrative import BRAND, UPDATE_LINK, CaseContext

log = logging.getLogger("dunning_iq.agent")

_CACHE_PATH = Path(__file__).resolve().parents[2] / ".agent_cache" / "decisions.json"

SYSTEM_PROMPT = (
    "You are Dunning IQ, an autonomous credit-control agent for a SaaS billing "
    "team. You handle failed recurring card payments end to end. You are precise, "
    "calm, and commercially sharp — you think like an operator who has run live "
    "billing, not a chatbot.\n\n"
    "For each failed payment you are given the normalised failure reason and the "
    "retry PLAYBOOK that the billing system will enforce (you cannot override it — "
    "e.g. stolen cards are never retried, fraud is escalated immediately). Your job "
    "is to produce the human-readable AUDIT TRAIL and the customer message:\n"
    "  • classification_reasoning: why this failure is what it is, and what it "
    "implies for recovery. Reference the specific failure type.\n"
    "  • strategy_reasoning: justify the retry cadence / escalation in the playbook "
    "in plain English a billing manager could audit.\n"
    "  • the customer message (when asked): on-brand, concise, leads with the fix.\n\n"
    "Never invent amounts, dates, or policy. Never promise refunds. Keep reasoning "
    "to 2-4 sentences — tight and specific, no filler. Always respond as JSON that "
    "matches the schema you are given."
)


class _ReasoningOnly(BaseModel):
    confidence: float = Field(ge=0, le=1)
    classification_reasoning: str
    strategy_reasoning: str


class _ReasoningWithMessage(_ReasoningOnly):
    message_subject: str
    message_body: str
    message_reasoning: str


# ── shared base ──────────────────────────────────────────────────────────────

class LiveLLMEngine(DecisionEngine):
    """Common scaffolding for live LLM-backed decision engines.

    Subclasses implement :meth:`_call_llm` to talk to their provider; the cache,
    fallback, and payload-to-Decision wiring are shared.
    """

    source: str = "llm"  # overridden by subclasses

    def __init__(self) -> None:
        self._client = None  # lazy
        self._cache = _load_cache()

    def analyze(
        self,
        ctx: CaseContext,
        pb: Playbook,
        *,
        tone: MessageTone | None = None,
        next_date: str | None = None,
        brand_voice: str | None = None,
    ) -> Decision:
        key = _cache_key(ctx, pb, tone, next_date, brand_voice, model=self._model_id())
        cached = self._cache.get(key)
        if cached is not None:
            return _decision_from_payload(ctx, cached, source=self.source)

        try:
            payload = self._call_llm(ctx, pb, tone, next_date, brand_voice)
        except Exception as exc:  # noqa: BLE001 — agent failures never break ingest
            log.warning("Live %s engine fell back to deterministic: %s", self.source, exc)
            fallback = super().analyze(
                ctx, pb, tone=tone, next_date=next_date, brand_voice=brand_voice
            )
            fallback.source = "replay"  # honestly record it wasn't the LLM
            return fallback

        self._cache[key] = payload
        _save_cache(self._cache)
        return _decision_from_payload(ctx, payload, source=self.source)

    # subclass hooks ----------------------------------------------------------

    def _model_id(self) -> str:
        raise NotImplementedError

    def _call_llm(self, ctx, pb, tone, next_date, brand_voice) -> dict:
        raise NotImplementedError


# ── Kimi (Moonshot, OpenAI-compatible) ───────────────────────────────────────

class LiveKimiEngine(LiveLLMEngine):
    """Live engine backed by Moonshot AI's Kimi via OpenAI-compatible JSON mode."""

    source = "kimi"

    def _model_id(self) -> str:
        return settings.kimi_model

    def _call_llm(self, ctx, pb, tone, next_date, brand_voice) -> dict:
        from openai import OpenAI  # local import keeps top-level deps cheap

        if self._client is None:
            self._client = OpenAI(
                api_key=settings.moonshot_api_key,
                base_url=settings.kimi_base_url,
            )

        schema = _ReasoningWithMessage if tone is not None else _ReasoningOnly
        user_prompt = _user_prompt(ctx, pb, tone, next_date, brand_voice)
        # Kimi/Moonshot supports OpenAI-style JSON mode but not strict
        # response-schema enforcement — inline the schema and validate ourselves.
        prompt_with_schema = (
            f"{user_prompt}\n\n"
            "## Required JSON shape (return ONLY this JSON, no markdown)\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )

        resp = self._client.chat.completions.create(
            model=settings.kimi_model,
            max_tokens=settings.agent_max_tokens,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_with_schema},
            ],
        )
        raw = resp.choices[0].message.content or ""
        try:
            data = json.loads(raw)
            parsed = schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Kimi returned invalid JSON for the agent schema: {exc}") from exc
        return parsed.model_dump()


# ── Claude (Anthropic SDK, structured output) ─────────────────────────────────

class LiveClaudeEngine(LiveLLMEngine):
    """Live engine backed by Anthropic Claude via ``messages.parse``."""

    source = "claude"

    def _model_id(self) -> str:
        return settings.claude_model

    def _call_llm(self, ctx, pb, tone, next_date, brand_voice) -> dict:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        schema = _ReasoningWithMessage if tone is not None else _ReasoningOnly
        prompt = _user_prompt(ctx, pb, tone, next_date, brand_voice)

        message = self._client.messages.parse(
            model=settings.claude_model,
            max_tokens=settings.agent_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        parsed = message.parsed_output
        if parsed is None:
            raise ValueError("Claude returned no structured output")
        return parsed.model_dump()


# Back-compat alias for any external import that used the old class name.
LiveDecisionEngine = LiveKimiEngine


# ── prompt + payload helpers ──────────────────────────────────────────────────

def _user_prompt(ctx: CaseContext, pb: Playbook, tone, next_date, brand_voice) -> str:
    lines = [
        "A recurring payment just failed. Analyse it.",
        "",
        "## Failed payment",
        f"- Customer: {ctx.full_name}" + (f" ({ctx.company})" if ctx.company else ""),
        f"- Plan: {ctx.plan_name}",
        f"- Amount at risk: {ctx.amount}",
        f"- Normalised failure reason: {ctx.failure_code.label} "
        f"(`{ctx.failure_code.value}`)",
        "",
        "## Enforced playbook (you cannot change this; explain it)",
        f"- Recoverable by retry: {pb.recoverable}",
        f"- Needs customer action: {pb.needs_customer_action}",
        f"- Max automated retries: {pb.max_attempts}",
        f"- Backoff (days between retries): {pb.backoff_days[: pb.max_attempts] or 'none'}",
        f"- Escalate after step {pb.escalate_after} to: {pb.escalation_target or 'n/a'}",
        f"- One-line strategy: {pb.summary}",
    ]
    if tone is not None:
        voice = brand_voice or "Warm, concise, respectful."
        lines += [
            "",
            "## Draft the first customer email",
            f"- Tone for this step: {tone.label} ({tone.value})",
            f"- Brand name: {BRAND}",
            f"- Brand voice to match: {voice}",
            f"- Update-payment link to include: {UPDATE_LINK}",
            f"- Next automatic retry date to mention (if recoverable): {next_date}",
            "Write a real email (subject + body). Use the customer's first name "
            f"({ctx.first_name}). Lead with how to fix it, not the failure.",
        ]
    return "\n".join(lines)


def _decision_from_payload(ctx: CaseContext, payload: dict, *, source: str) -> Decision:
    return Decision(
        failure_code=ctx.failure_code,
        confidence=float(payload["confidence"]),
        classification_reasoning=payload["classification_reasoning"],
        strategy_reasoning=payload["strategy_reasoning"],
        source=source,
        message_subject=payload.get("message_subject"),
        message_body=payload.get("message_body"),
        message_reasoning=payload.get("message_reasoning"),
    )


def _cache_key(ctx, pb, tone, next_date, brand_voice, *, model: str) -> str:
    raw = json.dumps(
        {
            "model": model,
            "name": ctx.full_name,
            "company": ctx.company,
            "amount": ctx.amount_minor,
            "currency": ctx.currency,
            "plan": ctx.plan_name,
            "code": ctx.failure_code.value,
            "tone": tone.value if tone else None,
            "next_date": next_date,
            "voice": brand_voice,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _load_cache() -> dict:
    try:
        return json.loads(_CACHE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2))
