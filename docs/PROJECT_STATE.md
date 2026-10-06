# PROJECT_STATE

Snapshot as of the end of this build session. Read this first if picking the
project back up.

## Status: **v1 complete and verified working**

- Backend: 30/30 pytest tests passing. Manually smoke-tested by booting the
  server and exercising every route (sessions, messages, events, alerts,
  reports, policy incl. dry-run, graph, settings, WebSocket).
- Frontend: `npm run build` passes (full TypeScript typecheck, all 9 routes
  compile). Manually smoke-tested against the real running backend —
  confirmed CORS works, fixtures load, pages render.
- The two together were run simultaneously and verified to talk to each
  other correctly (CORS preflight, WS message shapes match what each page
  expects).

## What's implemented
See `README.md` for the full feature list and `docs/SCOPE_DECISIONS.md` for
every deliberate simplification. In short: all four pipeline layers, all
four detectors, the XAI trust layer, the Groq-backed agent sandbox with 6
mock tools, the full REST API + WebSocket stream, and all 8 frontend pages
(Overview, Playground, Monitor, Alerts, Report detail, Graph, Policy,
Settings).

## Known gaps / good next steps
1. ~~No auth flow wired up.~~ **Done (item 5):** sign-up/login with
   bcrypt-hashed passwords and a JWT in an httpOnly cookie; the whole API
   and WebSocket require login. Set `JWT_SECRET` in `backend/.env`.
2. ~~No automated frontend tests.~~ **Done (item 6):** `npm test` (Vitest)
   and `npm run test:e2e` (Playwright, against the real backend).
3. **In-memory sandbox/agent conversation state** (`app/sandbox/agent.py`'s
   `_conversations` dict, `app/sandbox/tools.py`'s `_sandbox_state` dict)
   resets on backend restart. Fine for a demo; would need to move to the DB
   for anything persistent.
4. **Injection pattern bank is a ~25-pattern seed**, not the full 400+
   envisioned in the spec. Easy to extend — see
   `app/detection/data/injection_patterns.json`.
4b. ~~Behavioral anomaly used a hand-typed transition table.~~ **Done
   (item 2):** the backend now learns transition probabilities from its own
   allowed tool-call history at every startup
   (`app/detection/behavioral_graph.py`); status at `GET
   /api/behavioral-model` and on the Policy page.
5. ~~No real containerized sandboxing.~~ **Done:** every session now gets
   its own isolated Docker container (`app/sandbox/container_manager.py`,
   `SANDBOX_MODE=docker`). Requires Docker Desktop running; set
   `SANDBOX_MODE=memory` to run without it.
6. **Alerts now go through Celery + Redis to a SIEM webhook (item 4)**,
   but the live WebSocket bus is still an in-process `asyncio.Queue`, so
   the API itself is still single-process.

## How to verify it still works
```bash
# Backend
cd backend && source .venv/bin/activate && python -m pytest tests/ -q
# Real-container isolation tests (needs Docker Desktop running):
SENTINELAI_DOCKER_TESTS=1 python -m pytest tests/test_session_isolation.py -v
uvicorn app.main:app --reload --port 8000   # in one terminal

# Frontend
cd frontend && npm test            # unit tests (Vitest)
cd frontend && npm run test:e2e    # end-to-end (Playwright; first: npx playwright install chromium)
cd frontend && npm run dev                   # in another terminal
# visit http://localhost:3000/playground and try an attack preset
```
