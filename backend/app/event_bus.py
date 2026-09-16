"""
A minimal in-process pub/sub bus. Any interceptor calls `bus.publish(...)`.
Any number of subscribers (the Detection layer's dispatcher, the WebSocket
broadcaster) can `bus.subscribe()` and get an independent asyncio.Queue that
receives every message.

This intentionally mirrors the spec's asyncio.Queue based bus (§3.1) without
pulling in Celery/Redis, per the documented scope decision in docs/SCOPE_DECISIONS.md.
"""
import asyncio
from typing import AsyncIterator

from app.schemas import WSMessage


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[WSMessage]] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue[WSMessage] = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, message: WSMessage) -> None:
        for q in list(self._subscribers):
            await q.put(message)

    async def stream(self, q: asyncio.Queue) -> AsyncIterator[WSMessage]:
        while True:
            yield await q.get()


bus = EventBus()
