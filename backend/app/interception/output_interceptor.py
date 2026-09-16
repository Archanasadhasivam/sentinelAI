"""
Output Interceptor — report §4.1.

Buffers the sandbox agent's generated response *before* it's returned to
the user, so sensitive_data_leakage.py gets a chance to scan it for
API keys/PII the agent might otherwise echo back (e.g. after reading a
"file" that contained a secret). If blocked, the caller must substitute a
redacted/generic message instead of the raw agent output.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import process_event
from app.schemas import InterceptedEvent


async def intercept_output(
    db: AsyncSession,
    session_id: str,
    text: str,
) -> dict:
    event = InterceptedEvent(
        session_id=session_id,
        event_type="output",
        source="agent",
        payload={"text": text},
    )
    return await process_event(db, event)
