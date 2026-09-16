import pytest

from app.detection.behavioral_anomaly import behavioral_anomaly_detector
from app.schemas import InterceptedEvent


def _tool_event(session_id: str, tool: str) -> InterceptedEvent:
    return InterceptedEvent(
        session_id=session_id, event_type="tool_call", source="agent",
        payload={"tool_name": tool},
    )


@pytest.mark.asyncio
async def test_normal_sequence_not_flagged():
    session_id = "normal-seq"
    result = await behavioral_anomaly_detector.analyze(_tool_event(session_id, "file_read"))
    assert result.triggered is False
    result = await behavioral_anomaly_detector.analyze(_tool_event(session_id, "file_write"))
    assert result.triggered is False


@pytest.mark.asyncio
async def test_multi_step_exfiltration_chain_flagged():
    session_id = "exfil-chain"
    for tool in ["file_read", "run_shell", "fetch_url", "send_email"]:
        result = await behavioral_anomaly_detector.analyze(_tool_event(session_id, tool))
    # by the time 3+ distinct sensitive actions have chained together, this
    # should be flagged (build spec §8's multi-step exfiltration fixtures)
    assert result.triggered is True
