/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * Deviation from build spec §5.4: the spec calls for TanStack Query for
 * everything that isn't inherently push-based. For this MVP we use plain
 * fetch + React state/hooks instead, to keep the dependency surface small —
 * documented in docs/SCOPE_DECISIONS.md. Swapping in TanStack Query later
 * would only touch this file's call sites, not the API contract itself.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let code = "http_error";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(res.status, code, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; groq_configured: boolean }>("/health"),

  createSession: (label: string) =>
    request<{ id: string; label: string; created_at: string }>("/api/sandbox/session", {
      method: "POST",
      body: JSON.stringify({ label }),
    }),

  sendMessage: (sessionId: string, text: string) =>
    request<any>(`/api/sandbox/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  resetSession: (sessionId: string) =>
    request<{ ok: boolean }>(`/api/sandbox/${sessionId}/reset`, { method: "POST" }),

  getSessionEvents: (sessionId: string) =>
    request<{ events: any[] }>(`/api/sandbox/${sessionId}/events`),

  listEvents: (params: Record<string, string | number> = {}) => {
    const qs = new URLSearchParams(params as any).toString();
    return request<{ events: any[]; total: number }>(`/api/events${qs ? `?${qs}` : ""}`);
  },

  getEvent: (id: string) => request<any>(`/api/events/${id}`),

  listAlerts: (tier?: string) =>
    request<{ alerts: any[] }>(`/api/alerts${tier ? `?tier=${tier}` : ""}`),

  acknowledgeAlert: (id: string) =>
    request<{ ok: boolean }>(`/api/alerts/${id}/acknowledge`, { method: "POST" }),

  getReport: (verdictId: string) => request<any>(`/api/reports/${verdictId}`),

  getPolicy: () => request<{ policy: any; roc_weights_preview: number[] }>("/api/policy"),

  putPolicy: (policy: any) =>
    request<{ ok: boolean; policy: any }>("/api/policy", { method: "PUT", body: JSON.stringify(policy) }),

  dryRunPolicy: (policy: any, limit = 20) =>
    request<{ results: any[]; changed_count: number }>("/api/policy/dry-run", {
      method: "POST",
      body: JSON.stringify({ policy, limit }),
    }),

  getGraph: (sessionId: string) => request<{ nodes: any[]; edges: any[] }>(`/api/graph/${sessionId}`),

  getGroqStatus: () =>
    request<{ configured: boolean; degraded: boolean; models: Record<string, string> }>(
      "/api/settings/groq-status"
    ),

  getFixtures: () => request<{ fixtures: any[] }>("/api/fixtures"),
};
