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
- **No Vitest / Playwright suite.** Frontend correctness was checked via
  `next build` (full TypeScript typecheck across every page) and manual
  end-to-end smoke testing against the real running backend. Backend logic —
  where the actual security decisions happen — has 30 passing pytest tests.

## Backend
- **Celery/Redis → in-process `asyncio.Queue` bus** (`app/event_bus.py`).
  The spec's own §3.1 offers this as the lightweight option; there's exactly
  one backend process in this deployment, so a broker adds ops overhead with
  no benefit yet. `bus.publish()` is the only integration point if this ever
  needs to move to a real broker.
- **Session isolation is per-session in-memory state, not OS-level sandboxing**
  (`app/sandbox/tools.py`, `app/enforcement/session_isolation.py`). Tools are
  mocked (no real filesystem/network/shell access exists to isolate), so
  "isolation" here means each session gets its own dict-backed mock
  filesystem/mailbox/DB and its own behavioral-history/rate-limit counters —
  enough to demonstrate the *policy* of isolation without a container
  runtime to actually enforce it against real resources.
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
- **Auth is a single demo user, not full RBAC.** `DEMO_USERNAME`/`DEMO_PASSWORD`
  in `.env` exist as placeholders for a real auth layer; no login flow is
  wired into the frontend yet (see PROJECT_STATE.md).

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
