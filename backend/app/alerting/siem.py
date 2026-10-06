"""
SIEM webhook payload + signing.

Deliberately dependency-light (stdlib + httpx only) so the Celery worker
container can import it without the rest of the backend.

Every request carries two headers so the receiving SIEM can verify the
alert really came from SentinelAI and isn't a replay:

    X-SentinelAI-Timestamp: <unix seconds>
    X-SentinelAI-Signature: sha256=<hex HMAC-SHA256 of "<timestamp>.<body>">

To verify on the receiving side, recompute the HMAC over the same string
with the shared SIEM_WEBHOOK_SECRET and compare in constant time.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

SCHEMA_VERSION = "1.0"
SIGNATURE_HEADER = "X-SentinelAI-Signature"
TIMESTAMP_HEADER = "X-SentinelAI-Timestamp"


def build_payload(alert: dict) -> dict:
    """Wrap one alert in a stable, SIEM-friendly envelope."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "sentinelai",
        "event_kind": "security_alert",
        "alert": alert,
    }


def encode_body(payload: dict) -> bytes:
    # Compact + sorted keys so the signed bytes are exactly the sent bytes.
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign(body: bytes, secret: str, timestamp: int | None = None) -> dict[str, str]:
    ts = str(int(time.time()) if timestamp is None else timestamp)
    mac = hmac.new(secret.encode("utf-8"), ts.encode("ascii") + b"." + body, hashlib.sha256)
    return {TIMESTAMP_HEADER: ts, SIGNATURE_HEADER: f"sha256={mac.hexdigest()}"}


def verify(body: bytes, secret: str, timestamp: str, signature: str, max_age_seconds: int = 300) -> bool:
    """Reference verifier for SIEM-side code and tests."""
    try:
        if abs(time.time() - int(timestamp)) > max_age_seconds:
            return False
    except ValueError:
        return False
    expected = sign(body, secret, int(timestamp))[SIGNATURE_HEADER]
    return hmac.compare_digest(expected, signature)


class RetryableDeliveryError(Exception):
    """Network failure or 5xx/429 from the SIEM — worth retrying."""