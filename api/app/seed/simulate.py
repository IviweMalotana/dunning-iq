"""Fire realistic payment webhooks at a running Dunning IQ API.

    uv run python -m app.seed.simulate            # 12 events at localhost:8000
    uv run python -m app.seed.simulate 30         # 30 events
    SIMULATOR_TARGET=https://api.example python -m app.seed.simulate

Each iteration invents a customer + subscription and fires a `payment_failed`
event; a share of them are followed by a `payment_succeeded` on the same
subscription so you can watch the agent open a case and then recover it live.
"""

from __future__ import annotations

import json
import os
import random
import sys

import httpx

from app.core.config import settings
from app.core.security import sign_payload
from app.models.enums import FailureCode
from app.seed import catalog

RNG = random.Random()
TARGET = os.environ.get("SIMULATOR_TARGET", "http://localhost:8000").rstrip("/")
ENDPOINT = f"{TARGET}/webhooks/payments"

# Raw processor decline codes (what a real PSP sends) keyed by our FailureCode.
RAW_CODES = {
    FailureCode.INSUFFICIENT_FUNDS: "insufficient_funds",
    FailureCode.EXPIRED_CARD: "expired_card",
    FailureCode.DO_NOT_HONOR: "do_not_honor",
    FailureCode.CARD_DECLINED: "generic_decline",
    FailureCode.LOST_OR_STOLEN: "lost_card",
    FailureCode.AUTHENTICATION_REQUIRED: "authentication_required",
    FailureCode.PROCESSING_ERROR: "try_again_later",
    FailureCode.FRAUD_SUSPECTED: "fraudulent",
}


def _rid(prefix: str) -> str:
    return prefix + "".join(RNG.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12))


def _post(event: dict) -> dict:
    body = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if settings.webhook_signing_secret:
        headers["X-Dunning-Signature"] = sign_payload(settings.webhook_signing_secret, body)
    resp = httpx.post(ENDPOINT, content=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _make_actor() -> dict:
    first = RNG.choice(catalog.FIRST_NAMES)
    last = RNG.choice(catalog.LAST_NAMES)
    plan = RNG.choices([p for p in catalog.PLANS], weights=[p[3] for p in catalog.PLANS])[0]
    plan_name, amount, _segment, _ = plan
    company = f"{RNG.choice(catalog.COMPANY_PREFIX)} {RNG.choice(catalog.COMPANY_SUFFIX)}"
    domain = company.lower().replace(" ", "")
    return {
        "customer": {
            "external_id": _rid("cus_"),
            "email": f"{first.lower()}.{last.lower()}@{domain}.com",
            "name": f"{first} {last}",
            "company": company,
            "country": RNG.choice(catalog.COUNTRIES),
        },
        "subscription": {
            "external_id": _rid("sub_"),
            "plan_name": plan_name,
            "amount_minor": amount,
            "currency": "USD",
            "interval": "year" if "annual" in plan_name else "month",
        },
        "amount_minor": amount,
    }


def simulate(n: int = 12) -> None:
    print(f"▶  Firing {n} events at {ENDPOINT}\n")
    opened = recovered = appended = 0
    for i in range(n):
        actor = _make_actor()
        code = RNG.choices(
            [c for c, _ in catalog.FAILURE_WEIGHTS],
            weights=[w for _, w in catalog.FAILURE_WEIGHTS],
        )[0]
        fail_event = {
            "id": _rid("evt_"),
            "type": "payment_failed",
            "data": {
                "customer": actor["customer"],
                "subscription": actor["subscription"],
                "payment": {
                    "external_id": _rid("pay_"),
                    "amount_minor": actor["amount_minor"],
                    "currency": "USD",
                    "processor": RNG.choice(["stripe", "stripe", "paddle"]),
                    "failure_code": RAW_CODES[code],
                    "failure_message": catalog.DECLINE_MESSAGES[code],
                },
            },
        }
        res = _post(fail_event)
        action = res["action"]
        opened += action == "opened_case"
        appended += action == "appended_to_open_case"
        print(f"  {i + 1:>2}. payment_failed  {code.value:<22} → {action}: {res['detail']}")

        # A share of soft declines recover on the next charge.
        if action == "opened_case" and RNG.random() < 0.45:
            ok_event = {
                "id": _rid("evt_"),
                "type": "payment_succeeded",
                "data": {
                    "customer": actor["customer"],
                    "subscription": actor["subscription"],
                    "payment": {
                        "external_id": _rid("pay_"),
                        "amount_minor": actor["amount_minor"],
                        "currency": "USD",
                        "processor": "stripe",
                    },
                },
            }
            res2 = _post(ok_event)
            recovered += res2["action"] == "recovered_case"
            print(f"      ↳ payment_succeeded → {res2['action']}: {res2['detail']}")

    print(f"\n✅ Done. opened={opened}  recovered={recovered}  appended={appended}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
    try:
        simulate(count)
    except httpx.ConnectError:
        print(f"✗ Could not reach {ENDPOINT}. Is the API running? (make dev-api)")
        sys.exit(1)
