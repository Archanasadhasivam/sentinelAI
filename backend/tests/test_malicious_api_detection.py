import pytest

from app.detection.malicious_api_detection import malicious_api_detector
from app.schemas import InterceptedEvent


@pytest.mark.asyncio
async def test_allowlisted_domain_not_flagged():
    event = InterceptedEvent(
        session_id="s1", event_type="api_request", source="tool",
        payload={"url": "https://docs.python.org/3/"},
    )
    result = await malicious_api_detector.analyze(event)
    assert result.triggered is False


@pytest.mark.asyncio
async def test_non_allowlisted_domain_flagged():
    event = InterceptedEvent(
        session_id="s2", event_type="api_request", source="tool",
        payload={"url": "https://data-sink.example/upload"},
    )
    result = await malicious_api_detector.analyze(event)
    assert result.triggered is True


@pytest.mark.asyncio
async def test_dangerous_shell_command_flagged():
    event = InterceptedEvent(
        session_id="s3", event_type="tool_call", source="agent",
        payload={"tool_name": "run_shell", "command": "rm -rf / --no-preserve-root"},
    )
    result = await malicious_api_detector.analyze(event)
    assert result.triggered is True


@pytest.mark.asyncio
async def test_burst_of_outbound_calls_flagged():
    session_id = "burst-session"
    result = None
    for i in range(5):
        event = InterceptedEvent(
            session_id=session_id, event_type="api_request", source="tool",
            payload={"url": f"https://example.com/page{i}"},
        )
        result = await malicious_api_detector.analyze(event)
    assert result.triggered is True
