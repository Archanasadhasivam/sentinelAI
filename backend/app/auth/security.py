"""
Password hashing and login tokens.

- Passwords: bcrypt (salted, deliberately slow). Plain passwords are never
  stored or logged.
- Tokens: a signed JWT (HS256) holding the user id, valid for
  JWT_EXPIRE_HOURS, sent to the browser in an httpOnly cookie so page
  JavaScript can't read it (protects against XSS token theft).
"""
from __future__ import annotations

import secrets
import sys
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

COOKIE_NAME = "sentinelai_token"
ALGORITHM = "HS256"
MIN_PASSWORD_LENGTH = 8
# bcrypt only uses the first 72 bytes of a password; reject longer ones
# instead of silently ignoring the rest.
MAX_PASSWORD_BYTES = 72

_settings = get_settings()
if _settings.jwt_secret:
    _SECRET = _settings.jwt_secret
else:
    _SECRET = secrets.token_urlsafe(48)
    print(
        "[SentinelAI] WARNING: JWT_SECRET not set in backend/.env — using a random "
        "secret for this run, so everyone is logged out when the backend restarts.",
        file=sys.stderr,
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def password_problem(password: str) -> str | None:
    """Return a human-readable reason the password is unacceptable, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"password must be at most {MAX_PASSWORD_BYTES} bytes"
    return None


def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(hours=_settings.jwt_expire_hours)}
    return jwt.encode(payload, _SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """Return the user id if the token is valid and unexpired, else None."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[ALGORITHM], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


def cookie_kwargs() -> dict:
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "secure": _settings.cookie_secure,
        "samesite": "lax",
        "max_age": _settings.jwt_expire_hours * 3600,
        "path": "/",
    }