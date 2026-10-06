"use client";

/**
 * Login gate for the whole app (item 5). On every non-public page it asks
 * the backend "who am I?" (the httpOnly cookie is sent automatically). If
 * the answer is 401 it sends the browser to /login; otherwise it renders the
 * page and shares the logged-in user with the Nav.
 */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError, PUBLIC_PAGES, type AuthUser } from "@/lib/api";

interface AuthState {
  user: AuthUser | null;
  setUser: (u: AuthUser | null) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({ user: null, setUser: () => {}, logout: async () => {} });

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PAGES.includes(pathname);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<"checking" | "ready" | "error">("checking");

  useEffect(() => {
    if (isPublic || user) {
      setStatus("ready");
      return;
    }
    let cancelled = false;
    setStatus("checking");
    api
      .me()
      .then((r) => {
        if (cancelled) return;
        setUser(r.user);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        } else {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isPublic, pathname, router, user]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      router.replace("/login");
    }
  }, [router]);

  let content: ReactNode = children;
  if (!isPublic && status === "checking") {
    content = <p className="text-sm text-muted-foreground">Checking login…</p>;
  } else if (!isPublic && status === "error") {
    content = (
      <p className="text-sm text-danger" role="alert">
        Can&apos;t reach the backend. Make sure it is running on port 8000, then refresh.
      </p>
    );
  }

  return <AuthContext.Provider value={{ user, setUser, logout }}>{content}</AuthContext.Provider>;
}