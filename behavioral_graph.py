"""
behavioral_graph.py — Trained Behavioral Graph Model for SentinelAI

Gap-2 fix: the previous implementation (TRANSITION_PROB in app.py) was a
hand-typed dict of transition probabilities — a developer guessed the
numbers. That is a lookup table, not a trained model. This module replaces
it with an actual trained model: a weighted directed graph over tool-call
nodes whose edge probabilities are LEARNED from a training corpus of agent
session logs via frequency counting + Laplace (add-k) smoothing, using
networkx as the graph backend.

Model: first-order Markov transition graph. Nodes = tools (including the
synthetic "session_start" node). Edge weight u→v = P(next tool is v | last
tool was u), estimated from observed counts in TRAINING_SESSIONS below,
with additive smoothing so unseen-but-plausible transitions between two
KNOWN tools still get a small nonzero probability instead of one flat
constant, and transitions involving a tool the model has NEVER seen in
training score as a strong anomaly by design (UNSEEN_NODE_DEVIATION).

TRAINING_SESSIONS stands in for the organization's own historical agent
activity logs described in the project proposal's System Implementation
section — in production this corpus would come from real logs; here it is
synthetic but the training procedure (count → smooth → persist) is real,
and the learned model is written to trained_behavioral_graph.json so it
can be inspected/versioned like any other trained artifact.

Usage:
    from behavioral_graph import BehavioralGraphModel
    model = BehavioralGraphModel.load_or_train()
    deviation, prob, meta = model.path_deviation(prev_tool, requested_tool)
"""

import json
from collections import defaultdict
from pathlib import Path

import networkx as nx

MODEL_PATH = Path(__file__).parent / "trained_behavioral_graph.json"

# ──────────────────────────────────────────────────────────────────────────
# Training corpus — representative BENIGN agent session logs. Each session
# is a sequence of tool calls starting implicitly from "session_start".
# Frequencies ACROSS these sessions are what the model learns from — the
# numbers below are raw observed behavior, not probabilities; the model
# computes the probabilities itself at train time.
# ──────────────────────────────────────────────────────────────────────────
TRAINING_SESSIONS = [
    # -- Document / email workflows (most common pattern) --
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "send_email"],
    ["session_start", "read_document", "read_document", "send_email"],
    ["session_start", "read_document", "read_document", "send_email"],
    ["session_start", "read_document", "read_document", "read_document", "send_email"],
    ["session_start", "read_document", "summarize_document", "send_email"],
    ["session_start", "read_document", "summarize_document", "send_email"],
    ["session_start", "read_document", "summarize_document", "send_email"],

    # -- Calendar workflows --
    ["session_start", "read_calendar", "read_calendar"],
    ["session_start", "read_calendar", "read_calendar"],
    ["session_start", "read_calendar", "read_calendar"],
    ["session_start", "read_calendar", "send_email"],
    ["session_start", "read_calendar", "send_email"],
    ["session_start", "read_calendar", "send_email"],
    ["session_start", "read_calendar", "schedule_meeting"],
    ["session_start", "read_calendar", "schedule_meeting"],
    ["session_start", "read_calendar", "schedule_meeting", "send_email"],
    ["session_start", "read_calendar", "schedule_meeting", "send_email"],

    # -- Customer-support / CRM workflows --
    ["session_start", "read_crm_record", "send_email"],
    ["session_start", "read_crm_record", "send_email"],
    ["session_start", "read_crm_record", "update_crm_record"],
    ["session_start", "read_crm_record", "update_crm_record"],
    ["session_start", "read_crm_record", "update_crm_record", "send_email"],

    # -- Data-analysis workflows --
    ["session_start", "query_database", "generate_report"],
    ["session_start", "query_database", "generate_report"],
    ["session_start", "query_database", "generate_report", "send_email"],
    ["session_start", "query_database", "query_database", "generate_report"],

    # -- Rare-but-legitimate administrative action (kept low-frequency on
    #    purpose, so the model learns it's uncommon without being unseen) --
    ["session_start", "read_calendar", "backup_database"],
    ["session_start", "generate_report", "backup_database"],

    # -- Session-ending / no-op patterns --
    ["session_start", "read_document"],
    ["session_start", "read_calendar"],
    ["session_start", "query_database"],
]

# Laplace (add-k) smoothing constant. k>0 guarantees every SEEN source node
# still assigns a small nonzero probability to transitions it never
# observed, with the smoothing amount scaled by vocabulary size — a
# property of the trained model, not an arbitrary hand-picked constant.
SMOOTHING_K = 0.5

# Deviation assigned when either endpoint of a transition was NEVER seen
# anywhere in training — i.e. not just an unseen EDGE (smoothed-but-low
# probability above) but an unseen NODE (a tool the model has no
# behavioral history for at all). Intentionally the most severe case: an
# unmodeled tool is a stronger anomaly signal than a rare-but-known
# transition between two familiar tools.
UNSEEN_NODE_DEVIATION = 0.95


class BehavioralGraphModel:
    """A trained first-order Markov transition graph over agent tool calls."""

    def __init__(self, graph: nx.DiGraph, vocab: set):
        self.graph = graph
        self.vocab = vocab

    # ── Training ─────────────────────────────────────────────────────────
    @classmethod
    def train(cls, sessions=None) -> "BehavioralGraphModel":
        sessions = sessions or TRAINING_SESSIONS

        counts = defaultdict(lambda: defaultdict(int))
        vocab = set()
        for session in sessions:
            vocab.update(session)
            for a, b in zip(session, session[1:]):
                counts[a][b] += 1

        graph = nx.DiGraph()
        graph.add_nodes_from(vocab)

        n_vocab = len(vocab)
        for src in vocab:
            targets = counts.get(src, {})
            total = sum(targets.values())
            denom = total + SMOOTHING_K * n_vocab
            for dst in vocab:
                observed = targets.get(dst, 0)
                if observed > 0:
                    prob = (observed + SMOOTHING_K) / denom
                    graph.add_edge(src, dst, weight=round(prob, 4), observed_count=observed)
            # Smoothing prior for this source node's unseen outgoing edges —
            # computed once at train time, reused at inference time instead
            # of a flat shared constant.
            graph.nodes[src]["smoothed_unseen_prob"] = round(SMOOTHING_K / denom, 4)
            graph.nodes[src]["total_observed_outgoing"] = total

        return cls(graph, vocab)

    def save(self, path: Path = MODEL_PATH):
        data = {
            "vocab": sorted(self.vocab),
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "probability": d["weight"],
                    "observed_count": d["observed_count"],
                }
                for u, v, d in self.graph.edges(data=True)
            ],
            "node_smoothing": {
                n: {
                    "smoothed_unseen_prob": self.graph.nodes[n]["smoothed_unseen_prob"],
                    "total_observed_outgoing": self.graph.nodes[n]["total_observed_outgoing"],
                }
                for n in self.graph.nodes
            },
            "smoothing_k": SMOOTHING_K,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "BehavioralGraphModel":
        data = json.loads(path.read_text())
        vocab = set(data["vocab"])
        graph = nx.DiGraph()
        graph.add_nodes_from(vocab)
        for n, meta in data["node_smoothing"].items():
            graph.nodes[n]["smoothed_unseen_prob"] = meta["smoothed_unseen_prob"]
            graph.nodes[n]["total_observed_outgoing"] = meta["total_observed_outgoing"]
        for e in data["edges"]:
            graph.add_edge(
                e["source"], e["target"],
                weight=e["probability"], observed_count=e["observed_count"],
            )
        return cls(graph, vocab)

    @classmethod
    def load_or_train(cls, path: Path = MODEL_PATH, force_retrain: bool = False) -> "BehavioralGraphModel":
        if not force_retrain and path.exists():
            try:
                return cls.load(path)
            except Exception:
                pass  # stale/corrupt save file — fall through and retrain
        model = cls.train()
        try:
            model.save(path)
        except OSError:
            pass  # e.g. read-only filesystem — training still succeeded in memory
        return model

    # ── Inference ────────────────────────────────────────────────────────
    def path_deviation(self, prev_tool: str, requested_tool: str):
        """Returns (deviation, probability, meta) for an observed transition.

        deviation = 1 - probability — same contract as the old function, so
        app.py's downstream math (I_graph = 1 - deviation, etc.) is unchanged.
        meta explains WHY that probability was assigned, for the XAI report.
        """
        prev_tool = (prev_tool or "").strip()
        requested_tool = (requested_tool or "").strip()

        prev_seen = prev_tool in self.vocab
        next_seen = requested_tool in self.vocab

        if not prev_seen or not next_seen:
            unseen_tool = prev_tool if not prev_seen else requested_tool
            return UNSEEN_NODE_DEVIATION, 1 - UNSEEN_NODE_DEVIATION, {
                "basis": "unseen_node",
                "detail": (
                    f"'{unseen_tool}' never appeared in the training corpus — "
                    "no learned behavior exists for this tool."
                ),
            }

        if self.graph.has_edge(prev_tool, requested_tool):
            edge = self.graph[prev_tool][requested_tool]
            prob = edge["weight"]
            return 1 - prob, prob, {
                "basis": "observed_edge",
                "detail": (
                    f"Learned from {edge['observed_count']} occurrence(s) of "
                    f"{prev_tool} \u2192 {requested_tool} in training, Laplace-smoothed."
                ),
            }

        # Both nodes are known, but this exact pair was never observed
        # together — fall back to the source node's trained smoothing prior.
        fallback_prob = SMOOTHING_K / (SMOOTHING_K * len(self.vocab))
        prob = self.graph.nodes[prev_tool].get("smoothed_unseen_prob", fallback_prob)
        return 1 - prob, prob, {
            "basis": "smoothed_unseen_edge",
            "detail": (
                f"Both tools are known, but {prev_tool} \u2192 {requested_tool} was never "
                "observed in training; scored via that source node's Laplace-smoothed prior."
            ),
        }

    def stats(self):
        return {
            "trained_on_sessions": len(TRAINING_SESSIONS),
            "vocabulary_size": len(self.vocab),
            "learned_edges": self.graph.number_of_edges(),
            "smoothing_k": SMOOTHING_K,
            "tools": sorted(self.vocab),
        }
