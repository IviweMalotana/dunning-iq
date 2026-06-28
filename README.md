# Dunning IQ

**An AI agent that handles failed recurring payments end to end** — it classifies
*why* a payment failed, decides a retry strategy, drafts the customer dunning
message at the right escalation tone, and knows when to hand off to a human. Every
decision is logged with the agent's plain-English reasoning, so a billing operator
can audit exactly why it did what it did.

> Built by someone who has run live billing: a previous production direct-debit
> failure system + credit-control funnel grew billing capacity 7× and recovered
> material bad debt. Dunning IQ is the AI-native version of that work.

---

## What it does

1. **Ingests failed-payment events** — a Stripe/Paddle-shaped webhook endpoint,
   plus a simulator that fires realistic `payment_failed` / `payment_succeeded`
   events so the system is alive without a real PSP.
2. **Runs an LLM agent on every failure** — it classifies the failure reason
   (insufficient funds, expired card, do-not-honor, technical…), decides a retry
   schedule and backoff, drafts the customer message at the right tone, and
   decides when to escalate to a human or to credit control.
3. **Logs every decision with reasoning** — the audit trail is the product. Each
   retry, message, and escalation is stored with a timestamp and the agent's
   plain-English justification.
4. **A recovery dashboard** — at-risk vs recovered revenue, recovery rate over
   time, breakdown by failure reason, and a live queue of accounts in dunning.

## Architecture

```
                          ┌──────────────────────────────────────────┐
   Stripe / Paddle  ──▶   │  FastAPI (Railway)                        │
   webhooks  +            │                                           │
   event simulator  ──▶   │   /webhooks/payments  ─┐                  │
                          │                        ▼                  │
                          │                 Agent decision engine     │
                          │            (Anthropic Claude, official SDK)│
                          │           classify → retry → draft → route │
                          │                        │                  │
                          │                        ▼                  │
                          │   dunning_cases · dunning_events · messages│
                          │              (SQLAlchemy + Alembic)        │
                          └──────────────┬───────────────────────────┘
                                         │ REST (JSON)
                                         ▼
                          ┌──────────────────────────────────────────┐
                          │  Next.js 15 App Router (Vercel)           │
                          │  dashboard · queue · case detail · settings│
                          │  Tailwind · Recharts · skeleton/empty/error│
                          └──────────────────────────────────────────┘

   Data: Postgres (Railway) in production · SQLite locally for zero-setup demo
```

| Layer    | Tech                                                              |
| -------- | ---------------------------------------------------------------- |
| Frontend | Next.js 15 (App Router) · TypeScript · Tailwind CSS · Recharts   |
| Backend  | FastAPI · Python 3.12 · `uv` · SQLAlchemy 2 · Alembic            |
| Database | Postgres (Railway) — SQLite locally for a zero-setup demo        |
| Model    | Anthropic Claude via the official SDK (`ANTHROPIC_API_KEY`)      |
| Deploy   | Vercel (web) · Railway (api + Postgres)                          |

Repo layout:

```
/api    FastAPI backend  (app/, alembic/, pyproject.toml)
/web    Next.js frontend (src/app, src/components, src/lib)
```

## Run locally (zero setup)

Prereqs: **Node 20+**, **Python 3.12** (managed by `uv`), and [`uv`](https://docs.astral.sh/uv/).
You do **not** need Postgres or Docker locally — the app falls back to a SQLite file.

```bash
git clone <repo> && cd dunning-iq
cp .env.example .env          # optional: add ANTHROPIC_API_KEY for the live agent

make install                  # uv sync + npm install
make seed                     # migrate + seed a few hundred realistic accounts
make dev                      # api on :8000, web on :3000
```

Open <http://localhost:3000>. The demo is fully clickable with **no API key** —
seeded cases ship with real agent reasoning captured at seed time. Set
`ANTHROPIC_API_KEY` to have the live engine process *new* simulated events.

Fire a fresh batch of failures at the running API:

```bash
make simulate
```

## The agent (live vs. deterministic)

The decision engine sits behind a single seam (`app/agent/engine.py → analyze()`):

- **Live** — with `ANTHROPIC_API_KEY` set, every *new* failed-payment event is
  classified, planned, and drafted by **Claude (`claude-opus-4-8`)** via the
  official SDK with structured output. Results are cached to disk, so re-runs are
  free and offline.
- **Deterministic fallback** — with no key (or on any transient API error), the
  same seam produces the decision from a hand-written billing playbook, so the
  demo never breaks and webhooks are never dropped. Each decision records whether
  it was `claude` or `replay`, surfaced in the audit trail.

Either way, the **hard billing guardrails** (never retry a stolen card, escalate
fraud immediately, payday-aligned backoff) live in `app/agent/strategy.py` and
always apply — the LLM supplies the *reasoning and the customer prose*, not the
authority to do something a billing operator would veto.

```bash
make agent-demo                 # see the agent reason about a sample failure
make agent-demo CODE=expired_card
```

The seeded demo history is intentionally **deterministic and reproducible**; the
live agent runs on new events you fire with `make simulate`.

## Environment variables

| Var                        | Where      | Purpose                                                        |
| -------------------------- | ---------- | -------------------------------------------------------------- |
| `DATABASE_URL`             | api        | Postgres URL in prod; unset → local SQLite file                |
| `ANTHROPIC_API_KEY`        | api        | Enables the live Claude agent; demo works without it           |
| `AGENT_MODEL`              | api        | Claude model id (default `claude-opus-4-8`)                    |
| `WEBHOOK_SIGNING_SECRET`   | api        | Verifies inbound payment webhooks                              |
| `CORS_ORIGINS`             | api        | Comma-separated allowed origins for the web app                |
| `NEXT_PUBLIC_API_BASE_URL` | web        | Base URL the frontend uses to reach the API                    |

## Deploy

Vercel (web) + Railway (api + Postgres) — full instructions land in milestone 7.

## Project status

Built in milestones: **M0** scaffold ✅ · M1 schema + seed · M2 webhook + simulator
· M3 agent engine + reasoning log · M4 dashboard/queue/case-detail UI · M5 settings
· M6 case-study landing · M7 deploy notes.
