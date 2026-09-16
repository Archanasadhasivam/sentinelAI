from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.database import get_db
from app.models import VerdictRow

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{verdict_id}")
async def get_report(verdict_id: str, db: AsyncSession = Depends(get_db)):
    v = await db.get(VerdictRow, verdict_id)
    if v is None:
        raise api_error(404, "report_not_found", f"no TrustReport for verdict {verdict_id}")
    return {
        "verdict_id": v.id,
        "event_id": v.event_id,
        "decision": v.decision,
        "risk_score": v.risk_score,
        "likelihood": v.likelihood,
        "impact": v.impact,
        "alpha": v.alpha,
        "dominant_factor": v.dominant_factor,
        "structured_report": v.explanation,
        "narrative": v.narrative,
        "created_at": v.created_at.isoformat(),
    }
