from app.policy.policy_engine import policy_engine
from app.schemas import DetectionResult, InterceptedEvent


def compute_likelihood(results: list[DetectionResult], weights: dict[str, float]) -> tuple[float, str]:
    """
    L = weighted max of triggered detector scores (a single strongly-triggered
    detector should dominate — this mirrors the report's ROC-weighted
    combination rather than a plain average, which would dilute a single
    clear signal among three quiet ones).
    Returns (L, dominant_detector_name).
    """
    if not results:
        return 0.0, "none"

    best_name = "none"
    best_weighted = 0.0
    for r in results:
        w = weights.get(r.detector_name, 1.0)
        weighted = r.score * w
        if weighted > best_weighted:
            best_weighted = weighted
            best_name = r.detector_name

    return min(best_weighted, 1.0), best_name


def compute_impact(event: InterceptedEvent, action_impact: dict[str, float], floor: float) -> float:
    key = event.payload.get("tool_name") or event.event_type
    impact = action_impact.get(key, action_impact.get("default", 0.4))
    return max(impact, floor)


def compute_risk(event: InterceptedEvent, results: list[DetectionResult]) -> dict:
    cfg = policy_engine.get()
    weights = cfg.get("detector_weights", {})
    risk_cfg = cfg.get("risk", {})
    alpha = float(risk_cfg.get("alpha", 0.5))
    floor = float(risk_cfg.get("impact_floor", 0.1))

    likelihood, dominant = compute_likelihood(results, weights)
    impact = compute_impact(event, cfg.get("action_impact", {}), floor)
    risk_score = alpha * likelihood + (1 - alpha) * impact

    return {
        "likelihood": round(likelihood, 4),
        "impact": round(impact, 4),
        "alpha": alpha,
        "risk_score": round(min(max(risk_score, 0.0), 1.0), 4),
        "dominant_factor": dominant,
    }
