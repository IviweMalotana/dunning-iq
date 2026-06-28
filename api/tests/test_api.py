"""Dashboard, queue, and human-in-the-loop mutation API tests."""

from __future__ import annotations


def _open_case(client) -> str:
    evt = {
        "id": "evt_api", "type": "payment_failed",
        "data": {
            "customer": {"external_id": "cus_api", "email": "a@b.com", "name": "Avery Stone"},
            "subscription": {"external_id": "sub_api", "plan_name": "Growth (monthly)",
                             "amount_minor": 9900, "currency": "USD", "interval": "month"},
            "payment": {"external_id": "pay_api", "amount_minor": 9900, "currency": "USD",
                        "processor": "stripe", "failure_code": "insufficient_funds",
                        "failure_message": "nsf"},
        },
    }
    r = client.post("/webhooks/payments", json=evt)
    return r.json()["case_id"]


def test_dashboard_summary_shape(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    for key in ("at_risk_usd_minor", "recovery_rate", "total_cases", "needs_human"):
        assert key in body


def test_queue_and_case_detail(client):
    case_id = _open_case(client)
    q = client.get("/api/cases?status=open").json()
    assert q["total"] >= 1
    assert any(i["id"] == case_id for i in q["items"])

    d = client.get(f"/api/cases/{case_id}").json()
    assert d["failure_label"] == "Insufficient funds"
    assert len(d["events"]) >= 3          # opened, classified, retry-scheduled
    assert len(d["messages"]) == 1        # first drafted message
    assert d["messages"][0]["status"] == "draft"


def test_approve_message_marks_sent(client):
    case_id = _open_case(client)
    d = client.get(f"/api/cases/{case_id}").json()
    mid = d["messages"][0]["id"]
    r = client.post(f"/api/cases/{case_id}/messages/{mid}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "sent"
    # an audit event was logged for the human action
    d2 = client.get(f"/api/cases/{case_id}").json()
    assert any(e["actor"] == "human" and "approved" in e["title"].lower() for e in d2["events"])


def test_override_pause_and_resolve(client):
    case_id = _open_case(client)
    r = client.post(f"/api/cases/{case_id}/override", json={"action": "pause", "note": "customer called"})
    assert r.json()["status"] == "paused"
    r = client.post(f"/api/cases/{case_id}/override", json={"action": "resolve"})
    body = r.json()
    assert body["status"] == "recovered"
    assert body["recovered_minor"] == 9900


def test_case_not_found(client):
    assert client.get("/api/cases/nope").status_code == 404
