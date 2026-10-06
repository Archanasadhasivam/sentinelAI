"""Login tests (item 5): sign-up, login, logout, and that the API is gated."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth.security import COOKIE_NAME, create_token, decode_token, hash_password, verify_password
from app.main import app

PASSWORD = "correct-horse-battery"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --- unit -------------------------------------------------------------------

def test_password_is_hashed_not_stored_plain():
    h = hash_password(PASSWORD)
    assert h != PASSWORD and h.startswith("$2")
    assert verify_password(PASSWORD, h)
    assert not verify_password("wrong-password", h)


def test_token_roundtrip_and_tamper_rejected():
    token = create_token("user-123")
    assert decode_token(token) == "user-123"
    assert decode_token(token[:-2] + "xx") is None
    assert decode_token("not-a-jwt") is None


# --- API --------------------------------------------------------------------

@pytest.mark.asyncio
async def test_protected_route_requires_login():
    async with _client() as c:
        resp = await c.get("/api/alerts")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "not_authenticated"


@pytest.mark.asyncio
async def test_health_is_public():
    async with _client() as c:
        assert (await c.get("/health")).status_code == 200


@pytest.mark.asyncio
async def test_signup_sets_httponly_cookie_and_unlocks_api():
    async with _client() as c:
        resp = await c.post("/api/auth/signup", json={"email": _email(), "password": PASSWORD})
        assert resp.status_code == 200
        set_cookie = resp.headers["set-cookie"].lower()
        assert COOKIE_NAME in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie
        assert "password_hash" not in resp.text  # hash never sent to the browser
        assert (await c.get("/api/alerts")).status_code == 200
        assert (await c.get("/api/auth/me")).json()["user"]["email"].endswith("@example.com")


@pytest.mark.asyncio
async def test_signup_rejects_bad_input_and_duplicates():
    async with _client() as c:
        assert (await c.post("/api/auth/signup", json={"email": "not-an-email", "password": PASSWORD})).status_code == 400
        assert (await c.post("/api/auth/signup", json={"email": _email(), "password": "short"})).status_code == 400
        email = _email()
        assert (await c.post("/api/auth/signup", json={"email": email, "password": PASSWORD})).status_code == 200
        dup = await c.post("/api/auth/signup", json={"email": email.upper(), "password": PASSWORD})
        assert dup.status_code == 409


@pytest.mark.asyncio
async def test_login_logout_flow():
    email = _email()
    async with _client() as c:
        await c.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
        await c.post("/api/auth/logout")
        c.cookies.clear()
        assert (await c.get("/api/alerts")).status_code == 401

        bad = await c.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
        assert bad.status_code == 401 and bad.json()["error"]["code"] == "invalid_credentials"
        unknown = await c.post("/api/auth/login", json={"email": _email(), "password": PASSWORD})
        assert unknown.status_code == 401 and unknown.json()["error"]["code"] == "invalid_credentials"

        ok = await c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert ok.status_code == 200
        assert (await c.get("/api/alerts")).status_code == 200


def test_websocket_rejects_without_login():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events") as ws:
                ws.receive_json()