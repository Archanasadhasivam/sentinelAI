"""FastAPI dependencies that gate the API behind login."""
from fastapi import Depends, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.auth.security import COOKIE_NAME, decode_token
from app.database import AsyncSessionLocal, get_db
from app.models import User


async def require_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Attach to a router to make every route in it require login."""
    token = request.cookies.get(COOKIE_NAME)
    user_id = decode_token(token) if token else None
    user = await db.get(User, user_id) if user_id else None
    if user is None:
        raise api_error(401, "not_authenticated", "please log in")
    return user


async def websocket_user(websocket: WebSocket) -> User | None:
    """WebSockets can't use the HTTP 401 flow, so the handler checks this
    and closes the socket itself when it returns None."""
    token = websocket.cookies.get(COOKIE_NAME)
    user_id = decode_token(token) if token else None
    if not user_id:
        return None
    async with AsyncSessionLocal() as db:
        return await db.get(User, user_id)