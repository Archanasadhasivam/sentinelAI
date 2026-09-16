from app.enforcement import session_isolation


class EnforcementResult:
    def __init__(self, allowed: bool, reason: str) -> None:
        self.allowed = allowed
        self.reason = reason


def enforce(session_id: str, decision: str) -> EnforcementResult:
    """
    The single choke point the sandbox agent's tool executor must call
    through. Nothing downstream of this function should ever run a tool
    without an explicit `allowed=True` here.
    """
    state = session_isolation.record_decision(session_id, decision)

    if state.isolated:
        return EnforcementResult(
            allowed=False,
            reason="session isolated after repeated Block verdicts — reset it from Settings to continue",
        )

    if decision == "block":
        return EnforcementResult(allowed=False, reason="blocked by policy")

    if decision == "wait":
        return EnforcementResult(allowed=False, reason="held for human review — approve from Alerts to proceed")

    return EnforcementResult(allowed=True, reason="allowed")
