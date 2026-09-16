from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.database import get_db
from app.models import DetectionResultRow, Event, VerdictRow

router = APIRouter(prefix="/api/events", tags=["events"])


def _serialize_event(e: Event, detections=None, verdict=None) -> dict:
    return {
        "id": e.id,
        "session_id": e.session_id,
        "event_type": e.event_type,
        "source": e.source,
        "payload": e.payload,
        "status": e.status,
        "created_at": e.created_at.isoformat(),
        "detections": [
            {"detector_name": d.detector_name, "score": d.score, "triggered": d.triggered, "evidence": d.evidence}
            for d in (detections or [])
        ],
        "verdict": None if verdict is None else {
            "id": verdict.id,
            "decision": verdict.decision,
            "risk_score": verdict.risk_score,
            "likelihood": verdict.likelihood,
            "impact": verdict.impact,
            "dominant_factor": verdict.dominant_factor,
            "narrative": verdict.narrative,
        },
    }


@router.get("")
async def list_events(
    session_id: str | None = None,
    event_type: str | None = None,
    decision: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Event).order_by(Event.created_at.desc())
    if session_id:
        stmt = stmt.where(Event.session_id == session_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if decision:
        stmt = stmt.where(Event.status == decision)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.offset(offset).limit(limit)
    events = (await db.execute(stmt)).scalars().all()

    out = []
    for e in events:
        detections = (await db.execute(
            select(DetectionResultRow).where(DetectionResultRow.event_id == e.id)
        )).scalars().all()
        verdict = (await db.execute(
            select(VerdictRow).where(VerdictRow.event_id == e.id)
        )).scalars().first()
        out.append(_serialize_event(e, detections, verdict))

    return {"events": out, "total": total, "limit": limit, "offset": offset}


@router.get("/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, event_id)
    if e is None:
        raise api_error(404, "event_not_found", f"no event with id {event_id}")
    detections = (await db.execute(
        select(DetectionResultRow).where(DetectionResultRow.event_id == e.id)
    )).scalars().all()
    verdict = (await db.execute(
        select(VerdictRow).where(VerdictRow.event_id == e.id)
    )).scalars().first()
    return _serialize_event(e, detections, verdict)
