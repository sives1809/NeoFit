import * as React from "react";
import { useNavigate } from "@tanstack/react-router";
import { getToken, setToken } from "@/lib/api/client";
import { authApi, type AuthUser } from "@/lib/api/auth";
import { authService, type AuthCredentials } from "@/lib/auth";

type Status = "loading" | "authed" | "guest";

type AuthState = {
  status: Status;
  user: AuthUser | null;
  token: string | null;
  login: (creds: AuthCredentials) => Promise<void>;
  signup: (creds: AuthCredentials) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthCtx = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<Status>("loading");
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [token, setTokenState] = React.useState<string | null>(null);

  const persist = React.useCallback((t: string | null) => {
    setToken(t);
    setTokenState(t);
  }, []);

  const refresh = React.useCallback(async () => {
    const t = getToken();
    if (!t) {
      setUser(null);
      setStatus("guest");
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
      setStatus("authed");
    } catch {
      persist(null);
      setUser(null);
      setStatus("guest");
    }
  }, [persist]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const login = React.useCallback(
    async (creds: AuthCredentials) => {
      const res = await authService.login(creds);
      persist(res.token);
      setUser(res.user);
      setStatus("authed");
    },
    [persist],
  );

  const signup = React.useCallback(
    async (creds: AuthCredentials) => {
      const res = await authService.signup(creds);
      persist(res.token);
      setUser(res.user);
      setStatus("authed");
    },
    [persist],
  );

  const logout = React.useCallback(() => {
    persist(null);
    setUser(null);
    setStatus("guest");
  }, [persist]);

  const value: AuthState = { status, user, token, login, signup, logout, refresh };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = React.useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export function useRequireAuth() {
  const auth = useAuth();
  const navigate = useNavigate();
  React.useEffect(() => {
    if (auth.status === "guest") {
      navigate({ to: "/login" });
    }
  }, [auth.status, navigate]);
  return auth;
}
