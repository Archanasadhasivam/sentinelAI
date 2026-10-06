"""Sign-up / login / logout / current user (item 5). These routes are the
only /api routes that don't require login."""
import re

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import api_error
from app.auth.dependencies import require_user
from app.auth.security import (
    COOKIE_NAME,
    cookie_kwargs,
    create_token,
    hash_password,
    password_problem,
    verify_password,
)
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Checked against when the email doesn't exist, so a wrong email takes about
# as long as a wrong password (no timing hint about which accounts exist).
_DUMMY_HASH = hash_password("not-a-real-password")


class Credentials(BaseModel):
    email: str
    password: str


def _user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "created_at": user.created_at.isoformat()}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup")
async def signup(body: Credentials, response: Response, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(body.email)
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise api_error(400, "invalid_email", "please enter a valid email address")
    problem = password_problem(body.password)
    if problem:
        raise api_error(400, "weak_password", problem)

    existing = (await db.execute(select(User).where(User.email == email))).scalars().first()
    if existing is not None:
        raise api_error(409, "email_taken", "an account with this email already exists")

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response.set_cookie(value=create_token(user.id), **cookie_kwargs())
    return {"user": _user_out(user)}


@router.post("/login")
async def login(body: Credentials, response: Response, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(body.email)
    user = (await db.execute(select(User).where(User.email == email))).scalars().first()
    # Same message whether the email or the password is wrong, so the form
    # can't be used to find out which emails have accounts.
    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        raise api_error(401, "invalid_credentials", "incorrect email or password")
    if not verify_password(body.password, user.password_hash):
        raise api_error(401, "invalid_credentials", "incorrect email or password")

    response.set_cookie(value=create_token(user.id), **cookie_kwargs())
    return {"user": _user_out(user)}


@router.post("/logout")
async def logout(response: Response):
    kw = cookie_kwargs()
    response.delete_cookie(COOKIE_NAME, path=kw["path"], secure=kw["secure"], httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(require_user)):
    return {"user": _user_out(user)}