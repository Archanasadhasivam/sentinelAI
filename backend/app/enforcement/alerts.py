"""
Alert creation — report §4.8.

1. Save the alert to the database and push it to the dashboard over the
   WebSocket (instant, works even if Redis/SIEM are down).
2. Hand it to the Celery queue for delivery to the external SIEM webhook
   (app/alerting/celery_app.py), which retries on failure.
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.alerting.celery_app import enqueue_alert
from app.event_bus import bus
from app.models import AlertRow, Event
from app.schemas import WSMessage

TIER_FOR_DECISION = {"block": "critical", "wait": "warning", "allow": None}


async def maybe_create_alert(db: AsyncSession, event_id: str, decision: str, dominant_factor: str, risk_score: float) -> AlertRow | None:
    tier = TIER_FOR_DECISION.get(decision)
    if tier is None and risk_score < 0.3:
        return None
    if tier is None:
        tier = "info"

    message = {
        "critical": f"Blocked: {dominant_factor} pushed risk to {risk_score:.2f}",
        "warning": f"Held for review: {dominant_factor} raised risk to {risk_score:.2f}",
        "info": f"Low-risk signal from {dominant_factor} (risk {risk_score:.2f})",
    }[tier]

    alert = AlertRow(event_id=event_id, tier=tier, message=message)
    db.add(alert)
    await db.flush()
    await db.commit()
    await db.refresh(alert)

    alert_data = {
        "id": alert.id,
        "event_id": event_id,
        "tier": tier,
        "message": message,
        "created_at": alert.created_at.isoformat(),
    }
    await bus.publish(WSMessage(kind="alert", data=alert_data))

    # Extra context for the SIEM, which can't query our database.
    event = await db.get(Event, event_id)
    siem_alert = {
        **alert_data,
        "session_id": event.session_id if event else None,
        "event_type": event.event_type if event else None,
        "decision": decision,
        "dominant_factor": dominant_factor,
        "risk_score": round(risk_score, 4),
    }
    # Publishing to Redis is blocking I/O, so keep it off the event loop.
    await asyncio.to_thread(enqueue_alert, siem_alert)
    return alert