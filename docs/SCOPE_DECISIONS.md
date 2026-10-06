# Scope decisions

This build followed `SENTINELAI_BUILD_PROMPT.md` closely, but a handful of
things were deliberately simplified to ship a working, testable v1 in one
sitting rather than a partially-working attempt at the full spec. Every
deviation below is a conscious trade, not an oversight — each is noted
inline in the code near where it matters, too.

## Frontend stack
- **TanStack Query → plain `fetch` + React state** (`lib/api.ts`). The API
  surface is small enough that a thin fetch wrapper plus `useState`/`useEffect`
  covers every page without pulling in a caching library. Swapping in
  TanStack Query later only touches call sites, not the API contract.
- **shadcn/ui → hand-rolled Tailwind primitives** (`components/Card.tsx`,
  `Badge.tsx`). Same visual language (dark ops-dashboard, token-based
  colors), far fewer files and no CLI scaffolding step.
- **React Flow → static SVG circular layout** (`app/graph/[sessionId]/page.tsx`).
  The tool-call graph is real data (nodes = tools called, edges = observed
  transitions, red dashed = flagged by the behavioral anomaly detector) but
  isn't draggable/zoomable. Good enough to *see* a deviating chain; not a
  general graph-exploration tool.
- **Frontend tests: Vitest + Playwright** (item 6). Vitest + Testing
  Library unit-test `Badge`, `RiskGauge`, `TrustReportCard` and `lib/api.ts`
  (`frontend/tests/unit/`, run with `npm test`). Playwright (`frontend/e2e/`,
  run with `npm run test:e2e`) starts its own real backend (memory sandbox,
  no Groq, eager alert queue, throwaway DB) and frontend on ports 8100/3100
  and tests login redirects, sign-up/log-in/log-out, and an attack preset
  being blocked and alerted. `lib/ws.ts` has no unit tests — it's covered by
  the E2E run. Tests run locally only; no GitHub Actions workflow yet.

## Backend
- **Behavioral anomaly: trained graph model, learned from the app's own
  history** (item 2, `app/detection/behavioral_graph.py`). A networkx
  first-order Markov transition graph over tool calls (plus a
  `session_start` node). Edge probabilities are counted from this
  deployment's past **Allowed** tool calls in the database (Blocked/held
  calls are excluded so attacks aren't learned as normal), with Laplace
  smoothing (k = 0.5), and retrained every time the backend starts.
  deviation = 1 − probability; above 0.7 it counts as an anomaly. Until
  there are 20 allowed tool calls the model reports "not trained" and only
  the exfiltration-chain rule (3+ distinct sensitive tools in the last 5
  calls) runs. Training data only accumulates when a Groq key is set,
  because the degraded-mode agent makes no tool calls. The Streamlit
  demo's root `behavioral_graph.py` is a separate model and was not changed.
- **Alert pipeline: Celery + Redis + signed SIEM webhook** (item 4,
  `app/alerting/`). The backend still saves each alert and pushes it to the
  dashboard over the in-process `asyncio.Queue` bus (`app/event_bus.py`) —
  so the UI stays instant and works even if Redis or the SIEM is down — and
  then queues it for a Celery worker, which POSTs it to `SIEM_WEBHOOK_URL`
  signed with HMAC-SHA256 (`X-SentinelAI-Timestamp` +
  `X-SentinelAI-Signature`). Network errors, 5xx and 429 are retried up to
  5 times with exponential backoff; 4xx is logged and not retried. Redis and
  the worker run in Docker (`backend/docker-compose.yml`) because Celery
  doesn't officially support Windows. If Redis is down the alert is still
  saved and shown; only SIEM delivery is skipped, with a warning. The live
  WebSocket bus itself is still single-process.
- **Session isolation is a real per-session Docker container**
  (`app/sandbox/container_manager.py`). Each session's container is created
  with the session and runs with `--network none` (no network at all), a
  read-only root filesystem with a writable `/workspace` only, all
  capabilities dropped, `no-new-privileges`, a non-root user, and
  256 MB / 0.5 CPU / 64-process limits. `run_shell`, `file_read` and
  `file_write` execute inside it (10 s timeout, ~4 KB output cap, paths
  confined to `/workspace`); `send_email`, `query_db` and `fetch_url` stay
  mocked. `--network none` was chosen over host iptables rules because the
  demo runs on Docker Desktop for Windows, where host iptables isn't
  available. After 3 consecutive Blocks the session is quarantined: the
  container keeps running (for inspection) but every tool call is refused
  until Reset, which destroys and recreates it. `SANDBOX_MODE=memory` keeps
  the old in-memory mocks for pytest and machines without Docker.
- **Injection pattern bank has ~25 seed patterns, not 400+.** Organized into
  the same categories the spec calls for (role-override, system-prompt
  exfiltration, obfuscation/encoding, tool-abuse, Hinglish variants), with
  room to extend `app/detection/data/injection_patterns.json` — the detector
  code doesn't care how many patterns are in each category.
- **Policy calibration:** `action_impact.prompt` is set to `0.6` rather than
  a naive low number. A raw prompt hasn't *done* anything yet, but a
  successful injection is high-impact by nature (it can go on to steer
  arbitrary downstream tool calls), so this calibration lets two
  corroborating regex categories in one message alone reach the Block band
  even with the semantic (Groq) layer unavailable — see the comment in
  `app/policy/policies.yaml`. A single weaker signal correctly lands in Wait
  until the semantic layer or a human confirms it; this is the intended
  layered behavior, not a bug.
- **Login: users table + sign-up, no roles** (item 5, `app/auth/`).
  Anyone can sign up; passwords are bcrypt-hashed (min 8 chars); login
  issues an HS256 JWT (8 h) in an httpOnly, SameSite=Lax cookie. Every API
  route and the WebSocket require login except `/health` and `/api/auth/*`.
  All logged-in users see the same data — there is no RBAC or per-user
  data separation, and no password reset or email verification.

## What was *not* simplified
- The four-layer pipeline (Interception → Detection → Policy/Risk →
  Enforcement) runs for real, end to end, for every event type.
- The Groq semantic layer, TrustReport narrative generation, and the Agent
  Sandbox's tool-using reasoning loop are real integrations, not stubs —
  they just degrade gracefully (deterministic-only) without an API key,
  which is itself a spec requirement (§7.5), not a shortcut.
- ROC-derived detector weights are computed from a ranking via the documented
  formula (`app/api/routes_policy.py::roc_weights`), never hand-picked.
- The Risk formula `R = α·L + (1-α)·I` is exactly as specified, with `α` and
  the impact floor both live-editable in the Policy page.
