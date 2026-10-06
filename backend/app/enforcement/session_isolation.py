"""
Session Isolation — report §4.7.

Two parts work together:

1. Containment (app/sandbox/container_manager.py): every session runs its
   run_shell/file_read/file_write tools inside its own Docker container with
   no network (network_mode="none"), a read-only root filesystem, a writable
   /workspace only, all capabilities dropped, a non-root user, and CPU /
   memory / process limits. A session can never see another session's files
   or reach the network, whatever the agent is tricked into running.

2. Quarantine (this module): a session that racks up ISOLATION_THRESHOLD
   consecutive Block verdicts is flagged "isolated", and every further tool
   call is refused by action_enforcer.py until a human presses Reset. The
   container is deliberately left running while isolated, so its state can
   still be inspected; Reset destroys it and creates a fresh one.

With SANDBOX_MODE=memory (pytest / no Docker) part 1 falls back to
per-session in-memory mocks; part 2 behaves identically in both modes.
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
