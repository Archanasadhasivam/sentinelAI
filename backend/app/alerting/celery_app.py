"""
Celery app + the `deliver_alert` task.

The FastAPI backend saves every alert to the database and pushes it to the
UI over the WebSocket itself (so the dashboard stays instant even if Redis
or the SIEM is down), then calls `enqueue_alert()` to hand the alert to this
queue. A separate worker process (see backend/docker-compose.yml) picks it
up and POSTs it to the SIEM webhook, retrying on failure.

Settings are read from environment variables (and backend/.env via
python-dotenv), not app.config, so the worker container only needs
celery + redis + httpx:

    REDIS_URL            broker, default redis://localhost:6379/0
    SIEM_WEBHOOK_URL     empty -> SIEM delivery is switched off
    SIEM_WEBHOOK_SECRET  shared HMAC secret (required when URL is set)
    ALERT_QUEUE_MODE     celery (default) | eager (run inline, no Redis; tests)
"""
from __future__ import annotations

import logging
import os

import httpx
from celery import Celery

try:  # load backend/.env for the API process; harmless if absent
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - worker image may not ship dotenv
    pass

from app.alerting.siem import RetryableDeliveryError, build_payload, encode_body, sign

log = logging.getLogger("sentinelai.alerting")

MAX_RETRIES = 5
REQUEST_TIMEOUT_SECONDS = 10


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def queue_mode() -> str:
    return "eager" if _env("ALERT_QUEUE_MODE", "celery").lower() == "eager" else "celery"


def siem_enabled() -> bool:
    return bool(_env("SIEM_WEBHOOK_URL"))


celery_app = Celery("sentinelai", broker=_env("REDIS_URL", "redis://localhost:6379/0"))
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_acks_late=True,            # a crashed worker doesn't lose the alert
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    task_always_eager=queue_mode() == "eager",
    task_eager_propagates=False,
    # Fail fast if Redis is down, so a missing broker never slows the API.
    broker_connection_timeout=2,
    broker_transport_options={"socket_connect_timeout": 2, "socket_timeout": 5, "max_retries": 0},
)


def post_to_siem(alert: dict) -> int:
    """POST one alert to the SIEM. Returns the HTTP status; raises
    RetryableDeliveryError for failures worth retrying."""
    url = _env("SIEM_WEBHOOK_URL")
    secret = _env("SIEM_WEBHOOK_SECRET")
    if not url:
        return 0
    if not secret:
        raise ValueError("SIEM_WEBHOOK_SECRET must be set when SIEM_WEBHOOK_URL is set")

    body = encode_body(build_payload(alert))
    headers = {"Content-Type": "application/json", **sign(body, secret)}
    try:
        resp = httpx.post(url, content=body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise RetryableDeliveryError(f"network error: {exc}") from exc

    if resp.status_code >= 500 or resp.status_code == 429:
        raise RetryableDeliveryError(f"SIEM returned {resp.status_code}")
    if resp.status_code >= 400:
        # Bad URL/secret/payload — retrying won't help, so log and give up.
        log.error("SIEM rejected alert %s with %s: %s", alert.get("id"), resp.status_code, resp.text[:200])
    return resp.status_code


@celery_app.task(
    name="sentinelai.deliver_alert",
    autoretry_for=(RetryableDeliveryError,),
    retry_backoff=2,          # 2s, 4s, 8s, 16s, 32s
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def deliver_alert(alert: dict) -> int:
    status = post_to_siem(alert)
    log.info("alert %s delivered to SIEM (HTTP %s)", alert.get("id"), status)
    return status


def enqueue_alert(alert: dict) -> bool:
    """Called by the backend after an alert is saved. Never raises: if Redis
    is down the alert still exists in the DB/UI, only SIEM delivery is
    skipped (with a warning). Returns True if handed off."""
    if not siem_enabled():
        return False
    try:
        deliver_alert.apply_async(args=[alert], retry=False)
        return True
    except Exception as exc:  # broker unreachable, etc.
        log.warning("could not queue alert %s for SIEM delivery: %s", alert.get("id"), exc)
        return False