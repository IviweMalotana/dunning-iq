"""Policy editor + live-preview tests."""

from __future__ import annotations


def test_get_policy_defaults(client):
    p = client.get("/api/policy").json()
    assert p["max_retries"] >= 1
    assert isinstance(p["backoff_days"], list)
    assert p["base_tone"]


def test_update_policy_persists_and_clamps(client):
    r = client.patch("/api/policy", json={"max_retries": 99, "base_tone": "urgent"})
    body = r.json()
    assert body["max_retries"] == 8  # clamped
    assert body["base_tone"] == "urgent"
    assert client.get("/api/policy").json()["max_retries"] == 8


def test_update_rejects_bad_tone(client):
    assert client.patch("/api/policy", json={"base_tone": "nope"}).status_code == 422


def test_preview_reflects_proposed_values(client):
    a = client.post(
        "/api/policy/preview",
        json={"failure_code": "insufficient_funds", "max_retries": 4,
              "backoff_days": [2, 3, 5, 7], "base_tone": "friendly_reminder"},
    ).json()
    b = client.post(
        "/api/policy/preview",
        json={"failure_code": "insufficient_funds", "max_retries": 2,
              "backoff_days": [1, 4], "base_tone": "urgent"},
    ).json()
    assert a["max_attempts"] == 4 and b["max_attempts"] == 2
    assert b["backoff_days"] == [1, 4]
    assert a["message"]["tone"] == "friendly_reminder"
    assert b["message"]["tone"] == "urgent"
    assert a["message"]["subject"] != b["message"]["subject"]


def test_preview_hard_decline_has_no_message(client):
    r = client.post("/api/policy/preview", json={"failure_code": "fraud_suspected"}).json()
    assert r["max_attempts"] == 0
    assert r["message"] is None
    assert r["classification_reasoning"]
