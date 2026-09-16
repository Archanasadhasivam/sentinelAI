import pytest

from app.detection.fixtures.seed_payloads import SENSITIVE_DATA_LEAKAGE
from app.detection.sensitive_data_leakage import sensitive_data_leakage_detector
from app.schemas import InterceptedEvent


def _event(text: str) -> InterceptedEvent:
    return InterceptedEvent(session_id="test-session", event_type="output", source="agent", payload={"text": text})


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SENSITIVE_DATA_LEAKAGE)
async def test_secrets_are_flagged(payload):
    result = await sensitive_data_leakage_detector.analyze(_event(payload["text"]))
    assert result.triggered is True
    assert result.score >= 0.5


@pytest.mark.asyncio
async def test_clean_text_not_flagged():
    result = await sensitive_data_leakage_detector.analyze(_event("The weather today is sunny with a light breeze."))
    assert result.triggered is False
