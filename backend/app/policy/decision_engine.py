from app.policy.policy_engine import policy_engine


def decide(risk_score: float) -> str:
    cfg = policy_engine.get()
    thresholds = cfg.get("thresholds", {"block": 0.75, "wait": 0.45})
    if risk_score >= thresholds["block"]:
        return "block"
    if risk_score >= thresholds["wait"]:
        return "wait"
    return "allow"
