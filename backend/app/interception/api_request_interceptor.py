"""
API Request Interceptor — report §4.1.

Wraps the mock outbound HTTP-shaped calls the sandbox's "fetch_url" and
"send_email" tools make, so the allowlist/RiskChain logic in
malicious_api_detection.py always sees them as a distinct `api_request`
event type in addition to the `tool_call` event that triggered them.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import process_event
from app.schemas import InterceptedEvent


async def intercept_api_request(
    db: AsyncSession,
    session_id: str,
    url: str | None = None,
    method: str = "GET",
    body: str | None = None,
) -> dict:
    event = InterceptedEvent(
        session_id=session_id,
        event_type="api_request",
        source="tool",
        payload={"url": url, "method": method, "body": body or ""},
    )
    return await process_event(db, event)
