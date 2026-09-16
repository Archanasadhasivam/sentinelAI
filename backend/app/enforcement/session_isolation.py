"""
Session Isolation — report §4.7 (simplified).

The real proposal describes container/network-level isolation
(Docker/iptables) per agent session. For a student-scale local demo there is
no real container boundary to enforce, so this module tracks *logical*
isolation state instead: a session that racks up repeated Block verdicts
gets flagged "isolated" and further tool calls are refused outright until a
human resets it from the UI. This is a documented scope simplification
(see docs/SCOPE_DECISIONS.md) — swapping in real container isolation would
plug in here without touching the rest of the pipeline.
"""
from dataclasses import dataclass, field

ISOLATION_THRESHOLD = 3  # consecutive blocks before a session is isolated


@dataclass
class SessionState:
    consecutive_blocks: int = 0
    isolated: bool = False


_states: dict[str, SessionState] = {}


def get_state(session_id: str) -> SessionState:
    return _states.setdefault(session_id, SessionState())


def record_decision(session_id: str, decision: str) -> SessionState:
    state = get_state(session_id)
    if decision == "block":
        state.consecutive_blocks += 1
        if state.consecutive_blocks >= ISOLATION_THRESHOLD:
            state.isolated = True
    else:
        state.consecutive_blocks = 0
    return state


def reset_session(session_id: str) -> None:
    _states[session_id] = SessionState()
