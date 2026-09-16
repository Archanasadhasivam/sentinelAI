import asyncio

from app.detection.behavioral_anomaly import behavioral_anomaly_detector
from app.detection.malicious_api_detection import malicious_api_detector
from app.detection.prompt_injection import prompt_injection_detector
from app.detection.sensitive_data_leakage import sensitive_data_leakage_detector
from app.schemas import DetectionResult, InterceptedEvent

DETECTORS = [
    prompt_injection_detector,
    behavioral_anomaly_detector,
    sensitive_data_leakage_detector,
    malicious_api_detector,
]


async def run_all(event: InterceptedEvent) -> list[DetectionResult]:
    """Fan the event out to all four detectors concurrently (report §4: 'concurrently routed')."""
    results = await asyncio.gather(*(d.analyze(event) for d in DETECTORS), return_exceptions=True)
    clean: list[DetectionResult] = []
    for detector, result in zip(DETECTORS, results):
        if isinstance(result, Exception):
            clean.append(
                DetectionResult(
                    detector_name=detector.name,
                    score=0.0,
                    triggered=False,
                    metadata={"error": str(result)},
                )
            )
        else:
            clean.append(result)
    return clean
