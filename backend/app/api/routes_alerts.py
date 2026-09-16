from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.database import get_db
from app.models import AlertRow

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _serialize(a: AlertRow) -> dict:
    return {
        "id": a.id,
        "event_id": a.event_id,
        "tier": a.tier,
        "message": a.message,
        "acknowledged": a.acknowledged,
        "created_at": a.created_at.isoformat(),
    }


@router.get("")
async def list_alerts(
    tier: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertRow).order_by(AlertRow.created_at.desc())
    if tier:
        stmt = stmt.where(AlertRow.tier == tier)
    stmt = stmt.offset(offset).limit(limit)
    alerts = (await db.execute(stmt)).scalars().all()
    return {"alerts": [_serialize(a) for a in alerts]}


@router.get("/{alert_id}")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(AlertRow, alert_id)
    if a is None:
        raise api_error(404, "alert_not_found", f"no alert with id {alert_id}")
    return _serialize(a)


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(AlertRow, alert_id)
    if a is None:
        raise api_error(404, "alert_not_found", f"no alert with id {alert_id}")
    a.acknowledged = True
    await db.commit()
    return {"ok": True}
