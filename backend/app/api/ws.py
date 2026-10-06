from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.dependencies import websocket_user
from app.event_bus import bus

router = APIRouter(tags=["ws"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    if await websocket_user(websocket) is None:
        # 1008 = policy violation (not logged in). Logged-out users never get
        # this far in the UI: the frontend login gate sends them to /login.
        await websocket.close(code=1008)
        return
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