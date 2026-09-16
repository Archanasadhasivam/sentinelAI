"""
Malicious API/Tool-Call Detection Module — report §4.5.

- Allowlist check: outbound URLs/domains and shell commands are checked
  against a small allowlist; anything else scores high.
- RiskChain: a sliding window (last N seconds) tracks the *rate* of outbound
  calls per session — a burst of outbound requests (typical of automated
  exfiltration) raises the score even if each individual call looks benign.
"""
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from app.detection.base import extract_text
from app.schemas import DetectionResult, Evidence, InterceptedEvent

ALLOWED_DOMAINS = {
    "example.com",
    "api.internal.local",
    "docs.python.org",
    "wikipedia.org",
}

WINDOW_SECONDS = 20
BURST_THRESHOLD = 4  # 4+ outbound calls within WINDOW_SECONDS from one session

# session_id -> deque of timestamps of outbound api_request events
_call_windows: dict[str, deque] = defaultdict(deque)


class MaliciousApiDetector:
    name = "malicious_api_detection"

    async def analyze(self, event: InterceptedEvent) -> DetectionResult:
        if event.event_type not in ("api_request", "tool_call"):
            return DetectionResult(detector_name=self.name, score=0.0, triggered=False)

        evidence = []
        score = 0.0
        text = extract_text(event)

        url = event.payload.get("url")
        if url:
            domain = urlparse(url if "://" in url else f"https://{url}").netloc or url
            domain = domain.split(":")[0]
            if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
                score = max(score, 0.7)
                evidence.append(
                    Evidence(
                        detector=self.name,
                        label="allowlist_miss",
                        detail=f"destination '{domain}' is not on the outbound allowlist",
                        weight=0.7,
                    )
                )

        command = event.payload.get("command")
        if command and any(bad in command for bad in ["rm -rf", ":(){ :|:& };:", "curl ", "wget "]):
            score = max(score, 0.85)
            evidence.append(
                Evidence(
                    detector=self.name,
                    label="dangerous_command",
                    detail=f"command contains a high-risk pattern: {command[:60]!r}",
                    weight=0.85,
                )
            )

        # RiskChain sliding window (burst detection)
        now = time.monotonic()
        window = _call_windows[event.session_id]
        window.append(now)
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()

        if len(window) >= BURST_THRESHOLD:
            score = max(score, 0.6)
            evidence.append(
                Evidence(
                    detector=self.name,
                    label="riskchain_burst",
                    detail=f"{len(window)} outbound calls within {WINDOW_SECONDS}s — possible automated exfiltration",
                    weight=0.6,
                )
            )

        return DetectionResult(
            detector_name=self.name,
            score=score,
            triggered=score >= 0.5,
            evidence=evidence,
            metadata={"calls_in_window": len(window)},
        )


malicious_api_detector = MaliciousApiDetector()
