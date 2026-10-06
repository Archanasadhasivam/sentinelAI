import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, API_BASE } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "status " + status,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

let assign: ReturnType<typeof vi.fn>;

beforeEach(() => {
  assign = vi.fn();
  // jsdom's location can't be navigated, so replace it with a stub.
  vi.stubGlobal("location", { ...window.location, pathname: "/alerts", search: "?tier=critical", assign });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api request wrapper", () => {
  it("sends the login cookie with every request", async () => {
    const fetchMock = mockFetch(200, { alerts: [] });
    await api.listAlerts();
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/api/alerts`, expect.objectContaining({ credentials: "include" }));
  });

  it("sends JSON bodies for login", async () => {
    const fetchMock = mockFetch(200, { user: { id: "1", email: "a@b.co", created_at: "" } });
    await api.login("a@b.co", "secret-123");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ email: "a@b.co", password: "secret-123" });
  });

  it("turns the backend error envelope into an ApiError", async () => {
    mockFetch(404, { error: { code: "alert_not_found", message: "no alert with id x" } });
    const err = await api.acknowledgeAlert("x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: "alert_not_found", message: "no alert with id x" });
  });

  it("redirects to /login (keeping the current page) on 401", async () => {
    mockFetch(401, { error: { code: "not_authenticated", message: "please log in" } });
    await expect(api.listAlerts()).rejects.toBeInstanceOf(ApiError);
    expect(assign).toHaveBeenCalledWith("/login?next=" + encodeURIComponent("/alerts?tier=critical"));
  });

  it("does NOT redirect when the login call itself returns 401", async () => {
    mockFetch(401, { error: { code: "invalid_credentials", message: "incorrect email or password" } });
    await expect(api.login("a@b.co", "wrong-pass")).rejects.toMatchObject({ code: "invalid_credentials" });
    expect(assign).not.toHaveBeenCalled();
  });

  it("does not redirect when already on the login page", async () => {
    vi.stubGlobal("location", { ...window.location, pathname: "/login", search: "", assign });
    mockFetch(401, { error: { code: "not_authenticated", message: "please log in" } });
    await expect(api.listAlerts()).rejects.toBeInstanceOf(ApiError);
    expect(assign).not.toHaveBeenCalled();
  });
});