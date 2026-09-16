from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DetectionResultRow, Event

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/{session_id}")
async def get_session_graph(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Event)
        .where(Event.session_id == session_id, Event.event_type == "tool_call")
        .order_by(Event.created_at.asc())
    )
    events = (await db.execute(stmt)).scalars().all()

    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}

    prev_tool = None
    for e in events:
        tool = e.payload.get("tool_name", "unknown")
        nodes.setdefault(tool, {"id": tool, "label": tool, "call_count": 0})
        nodes[tool]["call_count"] += 1

        det_rows = (await db.execute(
            select(DetectionResultRow).where(
                DetectionResultRow.event_id == e.id,
                DetectionResultRow.detector_name == "behavioral_anomaly",
            )
        )).scalars().all()
        deviated = any(d.triggered for d in det_rows)

        if prev_tool is not None:
            key = (prev_tool, tool)
            edge = edges.setdefault(key, {"source": prev_tool, "target": tool, "count": 0, "deviated": False})
            edge["count"] += 1
            edge["deviated"] = edge["deviated"] or deviated

        prev_tool = tool

    return {
        "session_id": session_id,
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }
