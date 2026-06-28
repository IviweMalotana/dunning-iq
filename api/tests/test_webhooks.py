"""End-to-end webhook ingest + decisioning tests."""

from __future__ import annotations

import json

from app.core.security import sign_payload


def _failed(code: str, *, ext="pay_1", sub="sub_1", cus="cus_1", amount=9900) -> dict:
    return {
        "id": f"evt_{ext}",
        "type": "payment_failed",
        "data": {
            "customer": {"external_id": cus, "email": "t@acme.com", "name": "Taylor Brooks",
                         "company": "Acme"},
            "subscription": {"external_id": sub, "plan_name": "Growth (monthly)",
                             "amount_minor": amount, "currency": "USD", "interval": "month"},
            "payment": {"external_id": ext, "amount_minor": amount, "currency": "USD",
                        "processor": "stripe", "failure_code": code, "failure_message": "decline"},
        },
    }


def _succeeded(*, ext="pay_ok", sub="sub_1", cus="cus_1", amount=9900) -> dict:
    return {
        "id": f"evt_{ext}",
        "type": "payment_succeeded",
        "data": {
            "customer": {"external_id": cus, "email": "t@acme.com", "name": "Taylor Brooks"},
            "subscription": {"external_id": sub, "plan_name": "Growth (monthly)",
                             "amount_minor": amount, "currency": "USD"},
            "payment": {"external_id": ext, "amount_minor": amount, "currency": "USD",
                        "processor": "stripe"},
        },
    }


def test_failed_payment_opens_and_classifies_case(client):
    r = client.post("/webhooks/payments", json=_failed("insufficient_funds"))
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "opened_case"
    assert body["case_status"] == "in_progress"
    assert "Insufficient funds" in body["detail"]


def test_duplicate_event_is_idempotent(client):
    client.post("/webhooks/payments", json=_failed("insufficient_funds"))
    r = client.post("/webhooks/payments", json=_failed("insufficient_funds"))
    assert r.json()["action"] == "ignored_duplicate"


def test_fraud_escalates_immediately(client):
    r = client.post("/webhooks/payments", json=_failed("fraudulent", ext="pf", sub="sf", cus="cf"))
    assert r.json()["case_status"] == "escalated"


def test_success_recovers_open_case(client):
    client.post("/webhooks/payments", json=_failed("insufficient_funds"))
    r = client.post("/webhooks/payments", json=_succeeded())
    body = r.json()
    assert body["action"] == "recovered_case"
    assert body["case_status"] == "recovered"


def test_success_without_open_case_is_a_renewal(client):
    r = client.post("/webhooks/payments", json=_succeeded(ext="p_new", sub="s_new", cus="c_new"))
    assert r.json()["action"] == "recorded_payment"


def test_signature_rejected_when_secret_set(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "webhook_signing_secret", "whsec_test")
    payload = _failed("expired_card", ext="pe", sub="se", cus="ce")
    # No signature header → 401.
    r = client.post("/webhooks/payments", json=payload)
    assert r.status_code == 401
    # Correct signature → accepted.
    raw = json.dumps(payload).encode()
    r2 = client.post(
        "/webhooks/payments", content=raw,
        headers={"Content-Type": "application/json",
                 "X-Dunning-Signature": sign_payload("whsec_test", raw)},
    )
    assert r2.status_code == 200
