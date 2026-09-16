from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal, Protocol
import uuid

from pydantic import BaseModel, Field

EventType = Literal["prompt", "tool_call", "api_request", "output"]
Source = Literal["user", "rag", "agent", "tool"]
Decision = Literal["allow", "wait", "block"]


class Evidence(BaseModel):
    detector: str
    label: str
    detail: str
    weight: float = 1.0


class InterceptedEvent(BaseModel):
    """The one object every interceptor emits onto the event bus."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: EventType
    source: Source
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DetectionResult(BaseModel):
    detector_name: str
    score: float  # 0.0-1.0 normalized
    triggered: bool
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Detector(Protocol):
    name: str

    async def analyze(self, event: InterceptedEvent) -> DetectionResult: ...


class RiskVerdict(BaseModel):
    event_id: str
    likelihood: float
    impact: float
    alpha: float
    risk_score: float
    decision: Decision
    dominant_factor: str
    explanation: dict[str, Any]
    narrative: str | None = None


class WSMessage(BaseModel):
    """Envelope broadcast over /ws/events."""
    kind: Literal["event_created", "detection_result", "verdict", "alert"]
    data: dict[str, Any]
