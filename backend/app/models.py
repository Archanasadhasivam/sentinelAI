import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentSession(Base):
    """One Agent Sandbox conversation/run."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String, default="Untitled session")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    events: Mapped[list["Event"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Event(Base):
    """An InterceptedEvent persisted for the timeline / graph / reports."""
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    event_type: Mapped[str] = mapped_column(String)  # prompt | tool_call | api_request | output
    source: Mapped[str] = mapped_column(String)      # user | rag | agent | tool
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|allowed|wait|blocked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["AgentSession"] = relationship(back_populates="events")
    detection_results: Mapped[list["DetectionResultRow"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    verdict: Mapped["VerdictRow"] = relationship(
        back_populates="event", uselist=False, cascade="all, delete-orphan"
    )


class DetectionResultRow(Base):
    __tablename__ = "detection_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    detector_name: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)
    triggered: Mapped[bool] = mapped_column(Boolean)
    evidence: Mapped[list] = mapped_column(JSON)
    detector_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped["Event"] = relationship(back_populates="detection_results")


class VerdictRow(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), unique=True)
    likelihood: Mapped[float] = mapped_column(Float)   # L
    impact: Mapped[float] = mapped_column(Float)       # I
    risk_score: Mapped[float] = mapped_column(Float)   # R = alpha*L + (1-alpha)*I
    alpha: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String)      # allow | wait | block
    dominant_factor: Mapped[str] = mapped_column(String)
    explanation: Mapped[dict] = mapped_column(JSON)
    narrative: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped["Event"] = relationship(back_populates="verdict")


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    tier: Mapped[str] = mapped_column(String)  # info | warning | critical
    message: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    """Login accounts (item 5). Passwords are stored only as bcrypt hashes."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)