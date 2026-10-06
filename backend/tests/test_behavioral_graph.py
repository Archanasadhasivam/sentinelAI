"""Trained behavioral model tests (item 2): learning from the database,
using only Allowed tool calls, the untrained state, and anomaly scoring."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal
from app.detection import behavioral_graph as bg
from app.detection.behavioral_anomaly import behavioral_anomaly_detector
from app.models import AgentSession, Event, VerdictRow
from app.schemas import InterceptedEvent

# Normal behaviour: read a file, then write or email; sometimes query the DB.
NORMAL = [["file_read", "file_write"]] * 6 + [["file_read", "send_email"]] * 3 + [["query_db", "file_write"]] * 3


def _event(session_id: str, tool: str) -> InterceptedEvent:
    return InterceptedEvent(session_id=session_id, event_type="tool_call", source="agent", payload={"tool_name": tool})


@pytest.fixture
def trained_model(monkeypatch):
    model = bg.BehavioralGraphModel.train(NORMAL)
    assert model.trained  # 24 tool calls >= 20
    monkeypatch.setattr(bg.behavioral_model, "model", model)
    return model


# --- training -------------------------------------------------------------

def test_probabilities_are_learned_from_counts():
    model = bg.BehavioralGraphModel.train(NORMAL)
    p_write = model.graph["file_read"]["file_write"]["weight"]
    p_email = model.graph["file_read"]["send_email"]["weight"]
    assert p_write > p_email  # seen 6 times vs 3 times
    # Each node's outgoing probabilities (seen edges + smoothing for unseen) sum to 1.
    n_vocab = model.graph.number_of_nodes()
    for node in model.graph.nodes:
        seen = sum(d["weight"] for _, _, d in model.graph.out_edges(node, data=True))
        unseen = (n_vocab - model.graph.out_degree(node)) * model.graph.nodes[node]["smoothed_unseen_prob"]
        assert seen + unseen == pytest.approx(1.0)


def test_not_trained_below_minimum():
    assert not bg.BehavioralGraphModel.train([]).trained
    assert not bg.BehavioralGraphModel.train([["file_read", "file_write"]] * 9).trained  # 18 calls
    assert bg.BehavioralGraphModel.train([["file_read", "file_write"]] * 10).trained  # 20 calls


def test_deviation_explains_itself(trained_model):
    common, _, why = trained_model.path_deviation("file_read", "file_write")
    assert why["basis"] == "observed_transition" and common < 0.7
    rare, _, why = trained_model.path_deviation("file_write", "file_read")
    assert why["basis"] == "unseen_transition" and rare > 0.7
    unknown, _, why = trained_model.path_deviation("file_read", "run_shell")
    assert why["basis"] == "unseen_tool" and unknown == bg.UNSEEN_NODE_DEVIATION
    first, _, _ = trained_model.path_deviation(None, "file_read")  # first call of a session
    assert first < 0.7


@pytest.mark.asyncio
async def test_trains_only_on_allowed_tool_calls():
    async with AsyncSessionLocal() as db:
        s = AgentSession(label="bg-test")
        db.add(s)
        await db.flush()
        for tool, decision in [("file_read", "allow"), ("run_shell", "block"), ("fetch_url", "wait"), ("send_email", "allow")]:
            e = Event(session_id=s.id, event_type="tool_call", source="agent", payload={"tool_name": tool})
            db.add(e)
            await db.flush()
            db.add(VerdictRow(event_id=e.id, likelihood=0, impact=0, risk_score=0, alpha=0.5, decision=decision, dominant_factor="x", explanation={}))
        # A prompt event (not a tool call) is ignored even if allowed.
        p = Event(session_id=s.id, event_type="prompt", source="user", payload={"text": "hi"})
        db.add(p)
        await db.flush()
        db.add(VerdictRow(event_id=p.id, likelihood=0, impact=0, risk_score=0, alpha=0.5, decision="allow", dominant_factor="x", explanation={}))
        await db.commit()

        sessions = await bg.load_allowed_sessions(db)
    assert ["file_read", "send_email"] in sessions
    assert not any("run_shell" in x or "fetch_url" in x for x in sessions)


# --- detector -------------------------------------------------------------

@pytest.mark.asyncio
async def test_untrained_model_only_runs_chain_rule(monkeypatch):
    monkeypatch.setattr(bg.behavioral_model, "model", bg.BehavioralGraphModel.train([]))
    result = await behavioral_anomaly_detector.analyze(_event(f"u-{uuid.uuid4()}", "run_shell"))
    assert result.triggered is False
    assert result.metadata["model_trained"] is False and "not trained yet" in result.metadata["note"]


@pytest.mark.asyncio
async def test_normal_path_not_flagged_when_trained(trained_model):
    sid = f"n-{uuid.uuid4()}"
    for tool in ["file_read", "file_write"]:
        result = await behavioral_anomaly_detector.analyze(_event(sid, tool))
        assert result.triggered is False
    assert result.metadata["basis"] == "observed_transition"


@pytest.mark.asyncio
async def test_unusual_path_flagged_when_trained(trained_model):
    sid = f"a-{uuid.uuid4()}"
    await behavioral_anomaly_detector.analyze(_event(sid, "file_read"))
    result = await behavioral_anomaly_detector.analyze(_event(sid, "run_shell"))  # never seen
    assert result.triggered is True
    assert any(e.label == "path_deviation" for e in result.evidence)


# --- API ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_status_endpoint(trained_model):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/api/behavioral-model")).status_code == 401
        await c.post("/api/auth/signup", json={"email": "bg-api@example.com", "password": "test-password-123"})
        body = (await c.get("/api/behavioral-model")).json()
    assert body["trained"] is True and body["tool_calls"] == 24
    edge = next(e for e in body["edges"] if e["source"] == "file_read" and e["target"] == "file_write")
    assert edge["observed_count"] == 6