"""
Behavioral Anomaly Module — report §4.3.

Two checks on every tool call:

1. Path deviation (trained model, app/detection/behavioral_graph.py): how
   unlikely is this tool call given the previous one in the same session,
   according to transition probabilities LEARNED from this deployment's own
   allowed history? deviation = 1 - learned probability; above
   DEVIATION_THRESHOLD it counts as an anomaly. Skipped while the model is
   not trained yet (too little history) — the result says so.

2. Multi-step exfiltration chain (RiskChain rule): 3+ distinct sensitive
   actions within the last few tool calls of a session.
"""
from collections import defaultdict

from app.detection.behavioral_graph import behavioral_model
from app.schemas import DetectionResult, Evidence, InterceptedEvent

SENSITIVE_ACTIONS = {"send_email", "run_shell", "fetch_url", "query_db", "file_write"}
DEVIATION_THRESHOLD = 0.7
CHAIN_WINDOW = 5
CHAIN_MIN_DISTINCT = 3
CHAIN_SCORE = 0.65

# session_id -> list of tool names, most recent last
_session_history: dict[str, list[str]] = defaultdict(list)


class BehavioralAnomalyDetector:
    name = "behavioral_anomaly"

    async def analyze(self, event: InterceptedEvent) -> DetectionResult:
        if event.event_type != "tool_call":
            return DetectionResult(detector_name=self.name, score=0.0, triggered=False)

        action = event.payload.get("tool_name", "unknown")
        history = _session_history[event.session_id]
        prev = history[-1] if history else None
        model = behavioral_model.model

        evidence: list[Evidence] = []
        score = 0.0
        metadata: dict = {"model_trained": model.trained, "history_length": len(history) + 1}

        # 1. Path deviation from the trained model
        if model.trained:
            deviation, probability, why = model.path_deviation(prev, action)
            metadata.update({"path_deviation": round(deviation, 4), "transition_probability": round(probability, 4), "basis": why["basis"]})
            if deviation > DEVIATION_THRESHOLD:
                score = max(score, deviation)
                evidence.append(
                    Evidence(
                        detector=self.name,
                        label="path_deviation",
                        detail=f"unusual for this agent: {why['detail']} (deviation {deviation:.2f})",
                        weight=0.7,
                    )
                )
        else:
            metadata["note"] = (
                "behavioral model not trained yet — needs at least "
                f"{model.describe()['min_tool_calls_required']} allowed tool calls of history; "
                "only the exfiltration-chain rule ran"
            )

        # 2. Multi-step exfiltration chain
        recent_sensitive = {a for a in (history[-CHAIN_WINDOW:] + [action]) if a in SENSITIVE_ACTIONS}
        if len(recent_sensitive) >= CHAIN_MIN_DISTINCT:
            score = max(score, CHAIN_SCORE)
            evidence.append(
                Evidence(
                    detector=self.name,
                    label="exfiltration_chain",
                    detail=(
                        f"session chained {len(recent_sensitive)} distinct sensitive "
                        f"actions in a short window: {sorted(recent_sensitive)}"
                    ),
                    weight=0.8,
                )
            )

        history.append(action)
        if len(history) > 50:
            del history[:-50]

        return DetectionResult(
            detector_name=self.name,
            score=score,
            triggered=score >= 0.5,
            evidence=evidence,
            metadata=metadata,
        )


behavioral_anomaly_detector = BehavioralAnomalyDetector()