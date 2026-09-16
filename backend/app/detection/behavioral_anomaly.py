"""
Behavioral Anomaly Module — report §4.3 (simplified).

Full spec calls for a learned graph model of "normal" agent action sequences.
For a student-scale deployment we implement a *deterministic* stand-in that
still demonstrates the concept end-to-end:

- Each session keeps a rolling sequence of recent tool/action names.
- We maintain a small "expected transition" graph (which action typically
  follows which) seeded with sane defaults for the sandbox's tool set.
- `path_deviation = 1 - (observed_transition_frequency)` — an action that
  almost never follows the previous one scores high.
- A session that fires an unusually long chain of *distinct* sensitive
  actions in a short window also raises the score (covers "multi-step
  exfiltration chains" from §8's fixtures).

This is documented in docs/SCOPE_DECISIONS.md as a simplification of the
full graph-learning approach described in the research proposal.
"""
from collections import defaultdict

from app.detection.base import extract_text
from app.schemas import DetectionResult, Evidence, InterceptedEvent

SENSITIVE_ACTIONS = {"send_email", "run_shell", "fetch_url", "query_db", "file_write"}

# naive prior: action -> {next_action: expected_frequency}
EXPECTED_TRANSITIONS: dict[str, dict[str, float]] = {
    "file_read": {"file_write": 0.4, "query_db": 0.2, "fetch_url": 0.2, "send_email": 0.1},
    "query_db": {"file_write": 0.3, "send_email": 0.2, "fetch_url": 0.2},
    "fetch_url": {"file_write": 0.3, "query_db": 0.1, "send_email": 0.2},
    "file_write": {"send_email": 0.2, "run_shell": 0.1},
    "run_shell": {"send_email": 0.1, "fetch_url": 0.2},
    "send_email": {},
}

# session_id -> list of action names, most recent last
_session_history: dict[str, list[str]] = defaultdict(list)


class BehavioralAnomalyDetector:
    name = "behavioral_anomaly"

    async def analyze(self, event: InterceptedEvent) -> DetectionResult:
        if event.event_type != "tool_call":
            return DetectionResult(detector_name=self.name, score=0.0, triggered=False)

        action = event.payload.get("tool_name", "unknown")
        history = _session_history[event.session_id]

        evidence: list[Evidence] = []
        score = 0.0

        if history:
            prev = history[-1]
            expected = EXPECTED_TRANSITIONS.get(prev, {})
            freq = expected.get(action, 0.02)  # unseen transition = rare
            deviation = 1.0 - freq
            if deviation > 0.7:
                score = max(score, deviation)
                evidence.append(
                    Evidence(
                        detector=self.name,
                        label="path_deviation",
                        detail=f"'{prev}' -> '{action}' is an unusual transition for this agent (freq={freq:.2f})",
                        weight=0.7,
                    )
                )

        # multi-step exfiltration chain heuristic: 3+ distinct sensitive
        # actions within the last 5 tool calls of this session
        recent_sensitive = [a for a in (history[-5:] + [action]) if a in SENSITIVE_ACTIONS]
        if len(set(recent_sensitive)) >= 3:
            score = max(score, 0.65)
            evidence.append(
                Evidence(
                    detector=self.name,
                    label="exfiltration_chain",
                    detail=(
                        f"session chained {len(set(recent_sensitive))} distinct sensitive "
                        f"actions in a short window: {sorted(set(recent_sensitive))}"
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
            metadata={"history_length": len(history)},
        )


behavioral_anomaly_detector = BehavioralAnomalyDetector()
