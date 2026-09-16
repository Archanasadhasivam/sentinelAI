from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.event_bus import bus

router = APIRouter(tags=["ws"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    queue = bus.subscribe()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json({"kind": message.kind, "data": message.data})
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)
