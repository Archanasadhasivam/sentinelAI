"""
SentinelAI backend entrypoint.

Run with: uvicorn app.main:app --reload --port 8000  (from backend/)
"""
import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_alerts, routes_auth, routes_behavioral, routes_events, routes_graph, routes_policy, routes_reports, routes_sandbox, routes_settings, ws
from app.auth.dependencies import require_user
from app.config import get_settings
from app.database import AsyncSessionLocal, init_db
from app.detection.behavioral_graph import behavioral_model
from app.sandbox.container_manager import SandboxUnavailable, container_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.groq_enabled:
        print(
            "[SentinelAI] WARNING: GROQ_API_KEY not set (or looks like the .env.example "
            "placeholder). The semantic prompt-injection layer, TrustReport narrative "
            "generation, and the Agent Sandbox's live reasoning will all run in DEGRADED "
            "mode — deterministic detectors still run at full strength. Add a real key to "
            "backend/.env to enable them.",
            file=sys.stderr,
        )
    await init_db()

    # Item 2: retrain the behavioral model from this deployment's own
    # allowed tool-call history every time the backend starts.
    async with AsyncSessionLocal() as db:
        model = await behavioral_model.retrain(db)
    s = model.summary
    if model.trained:
        print(f"[SentinelAI] Behavioral model trained on {s.sessions} sessions / {s.tool_calls} allowed tool calls.", file=sys.stderr)
    else:
        print(
            f"[SentinelAI] Behavioral model not trained yet ({s.tool_calls} allowed tool calls so far, "
            f"needs {model.describe()['min_tool_calls_required']}). Only the exfiltration-chain rule runs "
            "until then — use the Sandbox with a Groq key to build history, then restart the backend.",
            file=sys.stderr,
        )

    if settings.sandbox_mode == "docker":
        if await asyncio.to_thread(container_manager.is_available):
            print("[SentinelAI] Session isolation: Docker sandbox mode (one container per session, no network).", file=sys.stderr)
        else:
            print(
                "[SentinelAI] WARNING: SANDBOX_MODE=docker but Docker is not reachable. "
                "Creating sandbox sessions will fail with 503 until Docker Desktop is running "
                "(or set SANDBOX_MODE=memory in backend/.env).",
                file=sys.stderr,
            )
    else:
        print("[SentinelAI] Session isolation: in-memory mode (SANDBOX_MODE=memory) — no containers.", file=sys.stderr)
    yield
    if settings.sandbox_mode == "docker":
        try:
            removed = await asyncio.to_thread(container_manager.remove_all)
            print(f"[SentinelAI] Removed {removed} sandbox container(s).", file=sys.stderr)
        except SandboxUnavailable:
            pass


app = FastAPI(title="SentinelAI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origin.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # `api_error()` already builds {"error": {"code", "message"}} as `detail`;
    # unwrap it so the client sees that shape at the top level (build spec §6).
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # No bare 500s with stack traces leaking to the client (build spec §6).
    print(f"[SentinelAI] Unhandled error on {request.url.path}: {exc!r}", file=sys.stderr)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "an unexpected error occurred"}},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "groq_configured": settings.groq_enabled, "sandbox_mode": settings.sandbox_mode}


# Public: /health (above) and the auth routes. Everything else needs login.
app.include_router(routes_auth.router)

_login_required = [Depends(require_user)]
app.include_router(routes_sandbox.router, dependencies=_login_required)
app.include_router(routes_events.router, dependencies=_login_required)
app.include_router(routes_alerts.router, dependencies=_login_required)
app.include_router(routes_reports.router, dependencies=_login_required)
app.include_router(routes_policy.router, dependencies=_login_required)
app.include_router(routes_graph.router, dependencies=_login_required)
app.include_router(routes_settings.router, dependencies=_login_required)
app.include_router(routes_behavioral.router, dependencies=_login_required)
app.include_router(ws.router)  # checks login itself — see app/api/ws.py