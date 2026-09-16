from sqlalchemy.ext.asyncio import AsyncSession

from app.event_bus import bus
from app.models import AlertRow
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

    await bus.publish(WSMessage(kind="alert", data={
        "id": alert.id,
        "event_id": event_id,
        "tier": tier,
        "message": message,
        "created_at": alert.created_at.isoformat(),
    }))
    return alert
