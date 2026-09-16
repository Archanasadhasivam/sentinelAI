"""
Tool Call Interceptor — report §4.1.

Every tool invocation the sandbox agent wants to make is wrapped here
*before* it runs. Execution is halted until the full
Detection -> Policy -> Enforcement pipeline (app.pipeline.process_event)
returns a verdict; only if `enforcement_allowed` is True does the caller
(app/sandbox/agent.py) actually run the mock tool.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import process_event
from app.schemas import InterceptedEvent


async def intercept_tool_call(
    db: AsyncSession,
    session_id: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    event = InterceptedEvent(
        session_id=session_id,
        event_type="tool_call",
        source="agent",
        payload={"tool_name": tool_name, **arguments},
    )
    return await process_event(db, event)
