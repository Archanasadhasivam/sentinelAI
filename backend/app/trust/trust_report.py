"""
Explainability / Trust Layer — report §4.8-ish / §5's XAI layer.

Takes the raw DetectionResults + risk computation and assembles a structured,
itemized explanation: which detector fired, on what evidence, and which
ROC-weighted factor dominated the final score. Optionally asks Groq to turn
that structure into a one-paragraph plain-English narrative for a
non-technical reviewer — degrades to "structured only" if Groq is
unavailable (§7.5).
"""
from app.groq_client import groq_client
from app.schemas import DetectionResult, InterceptedEvent

NARRATIVE_SYSTEM_PROMPT = (
    "You are writing a one-paragraph, plain-English trust report for a security "
    "analyst reviewing an AI agent security gateway's decision. Be concrete and "
    "cite the specific evidence given. Do not invent evidence not provided. "
    "Keep it under 120 words."
)


def build_structured_report(
    event: InterceptedEvent,
    results: list[DetectionResult],
    risk: dict,
    decision: str,
) -> dict:
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "decision": decision,
        "risk_score": risk["risk_score"],
        "likelihood": risk["likelihood"],
        "impact": risk["impact"],
        "alpha": risk["alpha"],
        "dominant_factor": risk["dominant_factor"],
        "detector_breakdown": [
            {
                "detector": r.detector_name,
                "score": r.score,
                "triggered": r.triggered,
                "evidence": [e.model_dump() for e in r.evidence],
                "metadata": r.metadata,
            }
            for r in results
        ],
    }


async def build_narrative(structured: dict) -> tuple[str | None, bool]:
    """Returns (narrative_text_or_None, degraded)."""
    from app.config import get_settings

    settings = get_settings()
    prompt = (
        f"Decision: {structured['decision'].upper()}\n"
        f"Risk score: {structured['risk_score']} "
        f"(likelihood={structured['likelihood']}, impact={structured['impact']}, "
        f"alpha={structured['alpha']})\n"
        f"Dominant factor: {structured['dominant_factor']}\n"
        f"Detector evidence:\n"
        + "\n".join(
            f"- {d['detector']} (score={d['score']:.2f}): "
            + "; ".join(e['detail'] for e in d['evidence']) if d["evidence"] else f"- {d['detector']}: no evidence"
            for d in structured["detector_breakdown"]
        )
    )
    reply, degraded = await groq_client.complete(
        model=settings.groq_reasoning_model,
        system=NARRATIVE_SYSTEM_PROMPT,
        user=prompt,
        max_tokens=200,
    )
    return reply, degraded
