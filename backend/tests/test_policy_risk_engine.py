from app.policy.decision_engine import decide
from app.policy.risk_engine import compute_likelihood
from app.schemas import DetectionResult


def test_compute_likelihood_picks_dominant_detector():
    results = [
        DetectionResult(detector_name="prompt_injection", score=0.9, triggered=True),
        DetectionResult(detector_name="behavioral_anomaly", score=0.2, triggered=False),
    ]
    weights = {"prompt_injection": 1.0, "behavioral_anomaly": 0.8}
    likelihood, dominant = compute_likelihood(results, weights)
    assert dominant == "prompt_injection"
    assert likelihood == 0.9


def test_compute_likelihood_empty_results():
    likelihood, dominant = compute_likelihood([], {})
    assert likelihood == 0.0
    assert dominant == "none"


def test_decision_thresholds():
    assert decide(0.1) == "allow"
    assert decide(0.5) == "wait"
    assert decide(0.9) == "block"
