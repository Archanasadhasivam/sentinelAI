import pytest

from app.detection.fixtures.seed_payloads import BENIGN_PROMPTS, DIRECT_INJECTION_EN, HINGLISH_INJECTION
from app.detection.prompt_injection import prompt_injection_detector
from app.schemas import InterceptedEvent


def _event(text: str) -> InterceptedEvent:
    return InterceptedEvent(session_id="test-session", event_type="prompt", source="user", payload={"text": text})


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", BENIGN_PROMPTS)
async def test_benign_prompts_not_triggered(payload):
    result = await prompt_injection_detector.analyze(_event(payload["text"]))
    assert result.triggered is False
    assert result.score < 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", DIRECT_INJECTION_EN)
async def test_direct_injection_english_triggers(payload):
    result = await prompt_injection_detector.analyze(_event(payload["text"]))
    assert result.triggered is True
    assert result.score >= 0.5
    assert len(result.evidence) >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", HINGLISH_INJECTION)
async def test_hinglish_injection_triggers(payload):
    result = await prompt_injection_detector.analyze(_event(payload["text"]))
    assert result.triggered is True
    assert result.score >= 0.5
