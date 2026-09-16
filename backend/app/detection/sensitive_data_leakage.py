"""
Sensitive Data Leakage Module — report §4.4.

Regex-based scanner for common secret/PII shapes in outbound content
(agent responses, outbound "emails", outbound "API requests"). This is the
detector primarily responsible for catching §8's "sensitive-data-leakage"
fixtures.
"""
import re

from app.detection.base import extract_text
from app.schemas import DetectionResult, Evidence, InterceptedEvent

PATTERNS = {
    "openai_api_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "groq_api_key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{20,}"),
    "email_address": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn_like": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "private_key_block": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
}

# Categories that are only concerning when they're being sent *out*, not just
# discussed. All of them are weighted; secrets/keys weigh much more than an
# email address on its own.
WEIGHTS = {
    "openai_api_key": 0.95,
    "groq_api_key": 0.95,
    "aws_access_key": 0.95,
    "generic_bearer_token": 0.85,
    "private_key_block": 0.98,
    "credit_card": 0.8,
    "ssn_like": 0.8,
    "email_address": 0.25,
}


class SensitiveDataLeakageDetector:
    name = "sensitive_data_leakage"

    async def analyze(self, event: InterceptedEvent) -> DetectionResult:
        # Most relevant on outputs and outbound API/email calls; still runs
        # on everything so a leaked secret pasted into a prompt is also caught.
        text = extract_text(event)
        evidence = []
        score = 0.0

        for label, pattern in PATTERNS.items():
            m = pattern.search(text)
            if m:
                weight = WEIGHTS.get(label, 0.5)
                score = max(score, weight)
                snippet = m.group(0)
                redacted = snippet[:4] + "…" + snippet[-2:] if len(snippet) > 8 else "…"
                evidence.append(
                    Evidence(
                        detector=self.name,
                        label=f"pattern:{label}",
                        detail=f"matched {label} pattern (redacted: {redacted})",
                        weight=weight,
                    )
                )

        return DetectionResult(
            detector_name=self.name,
            score=score,
            triggered=score >= 0.5,
            evidence=evidence,
            metadata={"event_type": event.event_type},
        )


sensitive_data_leakage_detector = SensitiveDataLeakageDetector()
