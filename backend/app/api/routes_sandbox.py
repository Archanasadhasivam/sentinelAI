import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.database import get_db
from app.enforcement.session_isolation import reset_session
from app.models import AgentSession, DetectionResultRow, Event, VerdictRow
from app.sandbox.agent import handle_message
from app.sandbox.container_manager import SandboxUnavailable
from app.sandbox.tools import create_sandbox, reset_sandbox

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class CreateSessionBody(BaseModel):
    label: str = "Untitled session"


class MessageBody(BaseModel):
    text: str


@router.post("/session")
async def create_session(body: CreateSessionBody, db: AsyncSession = Depends(get_db)):
    session = AgentSession(label=body.label)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Session isolation: spin up this session's own container now.
    try:
        await asyncio.to_thread(create_sandbox, session.id)
    except SandboxUnavailable as exc:
        await db.delete(session)
        await db.commit()
        raise api_error(503, "sandbox_unavailable", str(exc))

    return {"id": session.id, "label": session.label, "created_at": session.created_at.isoformat()}


@router.post("/{session_id}/message")
async def send_message(session_id: str, body: MessageBody, db: AsyncSession = Depends(get_db)):
    row = await db.get(AgentSession, session_id)
    if row is None:
        raise api_error(404, "session_not_found", f"no sandbox session with id {session_id}")

    result = await handle_message(db, session_id, body.text)
    return result


@router.post("/{session_id}/reset")
async def reset_sandbox_session(session_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(AgentSession, session_id)
    if row is None:
        raise api_error(404, "session_not_found", f"no sandbox session with id {session_id}")
    try:
        await asyncio.to_thread(reset_sandbox, session_id)
    except SandboxUnavailable as exc:
        raise api_error(503, "sandbox_unavailable", str(exc))
    reset_session(session_id)
    return {"ok": True}


@router.get("/{session_id}/events")
async def get_session_events(session_id: str, limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events = (await db.execute(stmt)).scalars().all()
    out = []
    for e in events:
        det_stmt = select(DetectionResultRow).where(DetectionResultRow.event_id == e.id)
        detections = (await db.execute(det_stmt)).scalars().all()
        verdict_stmt = select(VerdictRow).where(VerdictRow.event_id == e.id)
        verdict = (await db.execute(verdict_stmt)).scalars().first()
        out.append({
            "id": e.id,
            "event_type": e.event_type,
            "source": e.source,
            "payload": e.payload,
            "status": e.status,
            "created_at": e.created_at.isoformat(),
            "detections": [
                {"detector_name": d.detector_name, "score": d.score, "triggered": d.triggered, "evidence": d.evidence}
                for d in detections
            ],
            "verdict": None if verdict is None else {
                "decision": verdict.decision,
                "risk_score": verdict.risk_score,
                "likelihood": verdict.likelihood,
                "impact": verdict.impact,
                "dominant_factor": verdict.dominant_factor,
                "narrative": verdict.narrative,
            },
        })
    return {"events": out}
