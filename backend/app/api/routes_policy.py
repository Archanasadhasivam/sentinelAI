from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.database import get_db
from app.models import DetectionResultRow, Event
from app.policy.policy_engine import policy_engine
from app.policy.risk_engine import compute_impact, compute_likelihood
from app.schemas import DetectionResult, Evidence, InterceptedEvent

router = APIRouter(prefix="/api/policy", tags=["policy"])


def roc_weights(n: int) -> list[float]:
    """
    Rank Order Centroid weights: w_i = (1/n) * sum_{k=i}^{n} 1/k, for a
    ranking of n items from most (i=1) to least (i=n) important. Pure
    function so weights are always derived from a ranking, never hand-picked
    (build spec §3.3) — exposed here so the frontend can render/audit it.
    """
    if n <= 0:
        return []
    return [
        round((1.0 / n) * sum(1.0 / k for k in range(i, n + 1)), 4)
        for i in range(1, n + 1)
    ]


class PolicyBody(BaseModel):
    thresholds: dict
    risk: dict
    detector_weights: dict
    action_impact: dict


class DryRunBody(BaseModel):
    policy: PolicyBody
    limit: int = 20


@router.get("")
async def get_policy():
    cfg = policy_engine.get()
    n = len(cfg.get("detector_weights", {}))
    return {"policy": cfg, "roc_weights_preview": roc_weights(n)}


@router.put("")
async def put_policy(body: PolicyBody):
    try:
        policy_engine.save(body.model_dump())
    except Exception as exc:
        raise api_error(400, "invalid_policy", str(exc))
    return {"ok": True, "policy": policy_engine.get()}


@router.post("/reload")
async def reload_policy():
    cfg = policy_engine.get()  # get() already re-reads if mtime changed
    return {"ok": True, "policy": cfg}


@router.post("/dry-run")
async def dry_run(body: DryRunBody, db: AsyncSession = Depends(get_db)):
    """
    Re-score the last N events against a CANDIDATE policy body without
    persisting it (build spec §5.6's "Dry Run" button).
    """
    candidate = body.policy.model_dump()
    weights = candidate.get("detector_weights", {})
    risk_cfg = candidate.get("risk", {})
    alpha = float(risk_cfg.get("alpha", 0.5))
    floor = float(risk_cfg.get("impact_floor", 0.1))
    thresholds = candidate.get("thresholds", {"block": 0.75, "wait": 0.45})
    action_impact = candidate.get("action_impact", {})

    stmt = select(Event).order_by(Event.created_at.desc()).limit(body.limit)
    events = (await db.execute(stmt)).scalars().all()

    out = []
    for e in events:
        det_rows = (await db.execute(
            select(DetectionResultRow).where(DetectionResultRow.event_id == e.id)
        )).scalars().all()
        results = [
            DetectionResult(
                detector_name=d.detector_name,
                score=d.score,
                triggered=d.triggered,
                evidence=[Evidence(**ev) for ev in (d.evidence or [])],
                metadata=d.detector_metadata or {},
            )
            for d in det_rows
        ]
        pseudo_event = InterceptedEvent(
            session_id=e.session_id, event_type=e.event_type, source=e.source, payload=e.payload,
        )
        likelihood, dominant = compute_likelihood(results, weights)
        impact = compute_impact(pseudo_event, action_impact, floor)
        risk_score = round(min(max(alpha * likelihood + (1 - alpha) * impact, 0.0), 1.0), 4)

        if risk_score >= thresholds["block"]:
            new_decision = "block"
        elif risk_score >= thresholds["wait"]:
            new_decision = "wait"
        else:
            new_decision = "allow"

        out.append({
            "event_id": e.id,
            "event_type": e.event_type,
            "original_decision": e.status,
            "new_decision": new_decision,
            "new_risk_score": risk_score,
            "dominant_factor": dominant,
            "changed": new_decision != e.status,
        })

    return {"results": out, "changed_count": sum(1 for r in out if r["changed"])}
