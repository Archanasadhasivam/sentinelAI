"""
Prompt Interceptor — report §4.1.

Wraps every inbound message before it reaches the sandbox agent's context:
a direct user message, or a "RAG document"/"email" the agent is told to
read (this is how the indirect/RAG-embedded injection fixtures in §8 get
into the pipeline — they enter as `source="rag"` prompts, not user prompts).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline import process_event
from app.schemas import InterceptedEvent


async def intercept_prompt(
    db: AsyncSession,
    session_id: str,
    text: str,
    source: str = "user",
) -> dict:
    event = InterceptedEvent(
        session_id=session_id,
        event_type="prompt",
        source=source,  # "user" | "rag"
        payload={"text": text},
    )
    return await process_event(db, event)
