/**
 * Centralized API client for the AI Fitness backend (FastAPI).
 * - Base URL hardcoded per project spec.
 * - JWT pulled from localStorage and attached as Bearer.
 * - 401 responses clear the token and redirect to /login.
 */
export const API_BASE = "http://127.0.0.1:8000/api/v1";
const TOKEN_KEY = "fit_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; query?: Record<string, string | number | boolean | undefined> };

export async function apiFetch<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const { body, query, headers, ...rest } = opts;
  const url = new URL(API_BASE + path);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }

  const token = getToken();
  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((headers as Record<string, string>) ?? {}),
  };

  let res: Response | null = null;
  let attempts = 3;
  let delay = 1000;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      res = await fetch(url.toString(), {
        ...rest,
        headers: finalHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      break;
    } catch (err) {
      if (attempt === attempts) {
        throw new ApiError(
          "Cannot reach the backend at http://127.0.0.1:8000. Is the server running?",
          0,
          err,
        );
      }
      console.warn(`[API] fetch failed, retrying attempt ${attempt}/${attempts} in ${delay}ms...`, err);
      await new Promise((r) => setTimeout(r, delay));
      delay *= 2;
    }
  }

  if (!res) {
    throw new ApiError("No response received from the backend", 0, null);
  }

  if (res.status === 401) {
    setToken(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError("Unauthorized", 401, null);
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const msg =
      (data && typeof data === "object" && "detail" in (data as object)
        ? String((data as { detail: unknown }).detail)
        : null) ?? `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, data);
  }

  return data as T;
}

function safeJson(t: string): unknown {
  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

export async function checkBackendHealth(retries = 3, delayMs = 1000): Promise<boolean> {
  const healthUrl = "http://127.0.0.1:8000/health";
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(healthUrl);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "ok") {
          return true;
        }
      }
    } catch (e) {
      console.warn(`Health check attempt ${i + 1} failed:`, e);
    }
    if (i < retries - 1) {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  return false;
}
