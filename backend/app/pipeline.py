"""
Ties every layer together for a single InterceptedEvent. The four
interceptor modules in app/interception/ are thin: they build an
InterceptedEvent for their specific event type and call `process_event()`
here. Keeping the orchestration in one place avoids four copies of the same
"persist -> detect -> score -> decide -> enforce -> alert -> broadcast"
sequence (the report's diagram implies one linear pipeline after
interception, regardless of which interceptor produced the event).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.detection.dispatcher import run_all
from app.enforcement import action_enforcer, alerts
from app.event_bus import bus
from app.models import DetectionResultRow, Event, VerdictRow
from app.policy import decision_engine, risk_engine
from app.schemas import InterceptedEvent, WSMessage
from app.trust import trust_report


async def process_event(db: AsyncSession, event: InterceptedEvent) -> dict:
    # 1. Persist + broadcast the raw event immediately (pending), before a
    #    verdict exists — so the UI shows it the instant it's intercepted.
    row = Event(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type,
        source=event.source,
        payload=event.payload,
        status="pending",
    )
    db.add(row)
    await db.flush()
    await db.commit()

    await bus.publish(WSMessage(kind="event_created", data={
        "id": event.id,
        "session_id": event.session_id,
        "event_type": event.event_type,
        "source": event.source,
        "payload": event.payload,
        "status": "pending",
        "created_at": row.created_at.isoformat(),
    }))

    # 2. Detection layer: four detectors concurrently.
    results = await run_all(event)

    for r in results:
        db.add(DetectionResultRow(
            event_id=event.id,
            detector_name=r.detector_name,
            score=r.score,
            triggered=r.triggered,
            evidence=[e.model_dump() for e in r.evidence],
            detector_metadata=r.metadata,
        ))
        await bus.publish(WSMessage(kind="detection_result", data={
            "event_id": event.id,
            "detector_name": r.detector_name,
            "score": r.score,
            "triggered": r.triggered,
            "evidence": [e.model_dump() for e in r.evidence],
            "metadata": r.metadata,
        }))
    await db.commit()

    # 3. Policy & Risk Evaluation.
    risk = risk_engine.compute_risk(event, results)
    decision = decision_engine.decide(risk["risk_score"])

    # 4. Enforcement (actually gates tool execution for tool_call events).
    enforcement = action_enforcer.enforce(event.session_id, decision)

    # 5. XAI Trust Layer.
    structured = trust_report.build_structured_report(event, results, risk, decision)
    narrative, narrative_degraded = await trust_report.build_narrative(structured)

    verdict_row = VerdictRow(
        event_id=event.id,
        likelihood=risk["likelihood"],
        impact=risk["impact"],
        risk_score=risk["risk_score"],
        alpha=risk["alpha"],
        decision=decision,
        dominant_factor=risk["dominant_factor"],
        explanation=structured,
        narrative=narrative,
    )
    db.add(verdict_row)

    row.status = decision
    await db.commit()
    await db.refresh(verdict_row)

    await bus.publish(WSMessage(kind="verdict", data={
        "id": verdict_row.id,
        "event_id": event.id,
        "decision": decision,
        "risk_score": risk["risk_score"],
        "likelihood": risk["likelihood"],
        "impact": risk["impact"],
        "dominant_factor": risk["dominant_factor"],
        "narrative": narrative,
        "narrative_degraded": narrative_degraded,
        "enforcement_allowed": enforcement.allowed,
        "enforcement_reason": enforcement.reason,
    }))

    # 6. Alerts.
    await alerts.maybe_create_alert(db, event.id, decision, risk["dominant_factor"], risk["risk_score"])

    return {
        "event_id": event.id,
        "decision": decision,
        "risk": risk,
        "enforcement_allowed": enforcement.allowed,
        "enforcement_reason": enforcement.reason,
        "narrative": narrative,
        "narrative_degraded": narrative_degraded,
        "structured_report": structured,
    }
