from app.schemas import InterceptedEvent


def extract_text(event: InterceptedEvent) -> str:
    """Best-effort pull of 'the text to inspect' out of a heterogeneous payload."""
    payload = event.payload or {}
    for key in ("text", "content", "message", "body", "prompt", "output", "url", "command"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return str(payload)
