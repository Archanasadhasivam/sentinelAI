# SentinelAI

Multi-layer security, compliance, and trust middleware for autonomous AI
agents — a FastAPI backend implementing a four-layer pipeline
(**Interception → Detection → Policy & Risk → Enforcement**), plus an
Explainability/Trust layer, a live security dashboard, and a built-in
Groq-powered Agent Sandbox to attack and watch it work in real time.

See `docs/SCOPE_DECISIONS.md` for exactly what was simplified from the
original spec and why, and `docs/PROJECT_STATE.md` for current status and
suggested next steps.

## What it does

Every message sent to the sandboxed agent, every tool call it wants to make,
every outbound "API request" it triggers, and every reply it drafts, is
intercepted and run through:

1. **Detection** — 4 detectors run concurrently: prompt injection (regex +
   optional Groq semantic layer, with English/Hindi/Hinglish patterns),
   behavioral anomaly (flags unusual tool-call sequences), sensitive data
   leakage (API keys, private keys, PII in outputs), and malicious
   API/tool-call detection (domain allowlist, dangerous shell commands,
   burst-of-calls rate limiting).
2. **Policy & Risk** — combines detector scores into a Likelihood `L`
   (ROC-weighted), computes an Impact `I` for the action type, and scores
   `R = α·L + (1-α)·I`, mapped to **Allow / Wait / Block** via configurable
   thresholds.
3. **Enforcement** — actually gates whether the sandbox agent's tool call
   executes.
4. **Trust/XAI layer** — an itemized, evidence-backed "Trust Report" for
   every verdict, with an optional plain-English narrative from Groq.

All of this streams live to the frontend over a WebSocket, so you can watch
a message get intercepted, scored, and blocked in real time.

## Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional but recommended) a free [Groq API key](https://console.groq.com)
  — the app runs without one, just in a degraded mode (see below).

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Open .env and paste a real GROQ_API_KEY if you have one (optional).

uvicorn app.main:app --reload --port 8000
```

Verify it's up: `curl http://localhost:8000/health` should return
`{"status":"ok","groq_configured":...}`.

Run the test suite any time with:
```bash
python -m pytest tests/ -q
```

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install

cp .env.local.example .env.local
# defaults to http://localhost:8000 — only change this if your backend
# isn't running on the default port.

npm run dev
```

Open **http://localhost:3000**.

### 3. Try it out

- Go to **Playground**. Click **Attack presets** and pick one (try a
  "Hinglish jailbreak" or "Malicious support ticket" fixture) — watch the
  event stream on the right light up with detector scores and a verdict
  badge in real time.
- Check **Monitor** for the full filterable event log, **Alerts** for the
  tiered alert inbox, and click "Full report →" on any verdict for the
  itemized Trust Report.
- Visit **Policy** to see/edit the live risk formula and thresholds, and use
  **Dry run** to preview how a change would have re-scored recent events
  *without* saving it.
- **Settings** shows whether the Groq semantic layer is configured.

## Running without a Groq API key

The app is designed to degrade gracefully, not break, without one:
- The prompt-injection detector still runs its full regex/pattern layer
  (deterministic, no network call) — strongly corroborated attacks (two or
  more distinct injection categories in one message) still reach **Block**.
  Single weaker signals land in **Wait** for human review, which is the
  intended layered behavior.
- All other detectors (behavioral anomaly, sensitive data leakage, malicious
  API) are pure-Python and unaffected by Groq's availability.
- The Agent Sandbox's chat still runs the full security pipeline on every
  message, but its "brain" (tool-using reasoning) is replaced with a static
  notice, since that specifically requires an LLM.
- TrustReport narratives fall back to structured-only (no prose summary).

Add a key any time and restart the backend to light everything up.

## Project layout

```
backend/
  app/
    interception/    # 4 interceptors: prompt, tool_call, api_request, output
    detection/        # 4 detectors + dispatcher + seed fixtures
    policy/           # policy_engine (YAML, hot-reload), risk_engine, decision_engine
    enforcement/      # action_enforcer, session_isolation, alerts
    trust/            # XAI structured report + Groq narrative
    sandbox/          # mock tools + Groq-backed agent loop
    api/              # FastAPI routers + WebSocket
    pipeline.py        # ties every layer together for one event
    groq_client.py     # retry/backoff/circuit-breaker wrapper
  tests/               # pytest suite (30 tests)
frontend/
  app/                 # Next.js App Router pages
  components/          # shared UI (Card, Badge, TrustReportCard, etc.)
  lib/                 # api.ts (fetch client), ws.ts (WebSocket hook), types.ts
docs/
  SCOPE_DECISIONS.md   # every deliberate simplification, and why
  PROJECT_STATE.md     # current status + suggested next steps
```

## Troubleshooting

- **Frontend shows "Couldn't load presets — is the backend running?"** —
  make sure `uvicorn` is running on port 8000 and `NEXT_PUBLIC_API_URL` in
  `frontend/.env.local` points at it.
- **CORS errors in the browser console** — set `CORS_ORIGIN` in
  `backend/.env` to match wherever the frontend is actually served from.
- **`ModuleNotFoundError` running pytest** — make sure the venv is activated
  (`source .venv/bin/activate`) before running `pytest`.
