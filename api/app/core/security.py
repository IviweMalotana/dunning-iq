"""Webhook signature verification (HMAC-SHA256 over the raw request body)."""

from __future__ import annotations

import hashlib
import hmac


def sign_payload(secret: str, body: bytes) -> str:
    """Return the ``sha256=<hex>`` signature for a raw body — used by the simulator."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str | None, body: bytes, header: str | None) -> bool:
    """Constant-time verify. If no secret is configured, verification is skipped."""
    if not secret:
        return True  # demo / local: signing disabled
    if not header:
        return False
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, header)
