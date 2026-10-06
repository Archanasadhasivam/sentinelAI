"use client";

/** Shared form for /login and /signup. */
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";

function nextPath(): string {
  if (typeof window === "undefined") return "/";
  const next = new URLSearchParams(window.location.search).get("next");
  // Only allow same-site paths, never an external URL.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isSignup = mode === "signup";
  // True once React is running in the browser. Until then a click would do
  // nothing useful, so the E2E tests wait for data-ready="true".
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (isSignup && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const res = isSignup ? await api.signup(email, password) : await api.login(email, password);
      setUser(res.user);
      router.replace(nextPath());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Can't reach the backend. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  const inputClass =
    "w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary";

  return (
    <div className="w-full max-w-sm space-y-4">
      <h1 className="display text-3xl font-bold tracking-wide text-center">SENTINEL</h1>
      <Card>
        <CardHeader>
          <CardTitle>{isSignup ? "Create an account" : "Log in"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-3" data-ready={ready ? "true" : "false"}>
            <label className="block text-sm space-y-1">
              <span className="text-muted-foreground">Email</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
              />
            </label>
            <label className="block text-sm space-y-1">
              <span className="text-muted-foreground">Password</span>
              <input
                type="password"
                required
                minLength={isSignup ? 8 : undefined}
                autoComplete={isSignup ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
              />
            </label>
            {isSignup && (
              <label className="block text-sm space-y-1">
                <span className="text-muted-foreground">Confirm password</span>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={inputClass}
                />
              </label>
            )}
            {isSignup && <p className="text-xs text-muted-foreground">At least 8 characters.</p>}
            {error && (
              <p className="text-sm text-danger" role="alert" data-testid="form-error">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              {busy ? "Please wait…" : isSignup ? "Sign up" : "Log in"}
            </button>
          </form>
          <p className="mt-4 text-sm text-muted-foreground text-center">
            {isSignup ? (
              <>
                Already have an account? <Link href="/login" className="text-primary">Log in</Link>
              </>
            ) : (
              <>
                No account yet? <Link href="/signup" className="text-primary">Sign up</Link>
              </>
            )}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}