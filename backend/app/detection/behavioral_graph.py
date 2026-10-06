"""
Trained behavioral graph model for the backend — report §4.3 (item 2).

What it learns: how this deployment's agent NORMALLY moves between tools.
It is a first-order Markov transition graph (networkx DiGraph):

  - nodes = the sandbox tools, plus a synthetic "session_start" node so the
    first tool call of a session is scored too
  - edge u -> v weight = P(next tool is v | last tool was u)

Where the numbers come from: the app's OWN past sessions in the database.
For every session, the tool calls whose verdict was **Allow** are taken in
time order and the transitions between them are counted. Blocked and held
calls are never used, so attacks don't teach the model that attacks are
normal. Probabilities are those counts with Laplace (add-k) smoothing —
nothing is hand-typed.

When: retrained automatically every time the backend starts (app/main.py).
Until there are at least MIN_TRAINING_TOOL_CALLS allowed tool calls, the
model reports itself as not trained and the detector relies on its
exfiltration-chain rule only.

This is separate from the Streamlit demo's behavioral_graph.py in the repo
root, which uses a different tool vocabulary and a built-in corpus.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, VerdictRow

SESSION_START = "session_start"

# Laplace (add-k) smoothing: every known tool keeps a small nonzero
# probability for transitions it was never observed making.
SMOOTHING_K = 0.5

# A tool the model has never seen at all is the strongest anomaly signal.
UNSEEN_NODE_DEVIATION = 0.95

# Below this many allowed tool calls the model is "not trained yet".
MIN_TRAINING_TOOL_CALLS = 20


@dataclass
class TrainingSummary:
    sessions: int = 0
    tool_calls: int = 0
    transitions: int = 0


@dataclass
class BehavioralGraphModel:
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    summary: TrainingSummary = field(default_factory=TrainingSummary)

    # ── Training ──────────────────────────────────────────────────────────
    @classmethod
    def train(cls, sessions: list[list[str]]) -> "BehavioralGraphModel":
        """`sessions` = lists of tool names in time order (without session_start)."""
        counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        vocab: set[str] = {SESSION_START}
        summary = TrainingSummary()

        for tools in sessions:
            if not tools:
                continue
            summary.sessions += 1
            summary.tool_calls += len(tools)
            path = [SESSION_START, *tools]
            vocab.update(tools)
            for a, b in zip(path, path[1:]):
                counts[a][b] += 1
                summary.transitions += 1

        graph = nx.DiGraph()
        graph.add_nodes_from(vocab)
        n_vocab = len(vocab)
        for src in vocab:
            targets = counts.get(src, {})
            total = sum(targets.values())
            denom = total + SMOOTHING_K * n_vocab
            for dst, observed in targets.items():
                graph.add_edge(src, dst, weight=(observed + SMOOTHING_K) / denom, observed_count=observed)
            graph.nodes[src]["smoothed_unseen_prob"] = SMOOTHING_K / denom
            graph.nodes[src]["total_observed_outgoing"] = total

        return cls(graph=graph, summary=summary)

    @property
    def trained(self) -> bool:
        return self.summary.tool_calls >= MIN_TRAINING_TOOL_CALLS

    # ── Inference ─────────────────────────────────────────────────────────
    def path_deviation(self, prev_tool: str | None, tool: str) -> tuple[float, float, dict]:
        """Return (deviation, probability, explanation) for prev_tool -> tool.
        deviation = 1 - learned probability."""
        prev = prev_tool or SESSION_START
        for name in (prev, tool):
            if name not in self.graph:
                return UNSEEN_NODE_DEVIATION, 1 - UNSEEN_NODE_DEVIATION, {
                    "basis": "unseen_tool",
                    "detail": f"'{name}' never appeared in this agent's allowed history",
                }

        if self.graph.has_edge(prev, tool):
            edge = self.graph[prev][tool]
            prob = edge["weight"]
            return 1 - prob, prob, {
                "basis": "observed_transition",
                "detail": (
                    f"'{prev}' -> '{tool}' was seen {edge['observed_count']} time(s) in "
                    f"training (learned probability {prob:.2f})"
                ),
            }

        prob = self.graph.nodes[prev]["smoothed_unseen_prob"]
        return 1 - prob, prob, {
            "basis": "unseen_transition",
            "detail": (
                f"both tools are known, but '{prev}' -> '{tool}' was never seen in "
                f"training (smoothed probability {prob:.2f})"
            ),
        }

    def describe(self) -> dict:
        """Status for the API / Policy page."""
        return {
            "trained": self.trained,
            "min_tool_calls_required": MIN_TRAINING_TOOL_CALLS,
            "sessions": self.summary.sessions,
            "tool_calls": self.summary.tool_calls,
            "transitions": self.summary.transitions,
            "tools": sorted(n for n in self.graph.nodes if n != SESSION_START),
            "smoothing_k": SMOOTHING_K,
            "edges": sorted(
                (
                    {
                        "source": u,
                        "target": v,
                        "probability": round(d["weight"], 4),
                        "observed_count": d["observed_count"],
                    }
                    for u, v, d in self.graph.edges(data=True)
                ),
                key=lambda e: (e["source"], -e["probability"]),
            ),
        }


async def load_allowed_sessions(db: AsyncSession) -> list[list[str]]:
    """Allowed tool calls from the database, grouped by session, in time order."""
    stmt = (
        select(Event.session_id, Event.payload)
        .join(VerdictRow, VerdictRow.event_id == Event.id)
        .where(Event.event_type == "tool_call", VerdictRow.decision == "allow")
        .order_by(Event.session_id, Event.created_at)
    )
    sessions: dict[str, list[str]] = defaultdict(list)
    for session_id, payload in (await db.execute(stmt)).all():
        tool = (payload or {}).get("tool_name")
        if isinstance(tool, str) and tool:
            sessions[session_id].append(tool)
    return list(sessions.values())


class _ModelHolder:
    """The model currently in use. Starts empty (not trained)."""

    def __init__(self) -> None:
        self.model = BehavioralGraphModel.train([])

    async def retrain(self, db: AsyncSession) -> BehavioralGraphModel:
        self.model = BehavioralGraphModel.train(await load_allowed_sessions(db))
        return self.model


behavioral_model = _ModelHolder()