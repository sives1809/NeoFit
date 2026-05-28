import { apiFetch } from "./client";

export type Session = {
  id: string | number;
  created_at?: string;
  measurements?: Record<string, number | string>;
  [k: string]: unknown;
};

export const sessionsApi = {
  list: async () => {
    const list = await apiFetch<any[]>("/sessions");
    return list.map(mapSession);
  },
  create: (payload: Record<string, unknown>) =>
    apiFetch<Session>("/sessions", { method: "POST", body: payload }),
  get: async (id: string | number) => {
    const s = await apiFetch<any>(`/sessions/${id}`);
    return mapSession(s);
  },
  remove: (id: string | number) =>
    apiFetch<{ ok: boolean }>(`/sessions/${id}`, { method: "DELETE" }),
};

function mapSession(s: any): Session {
  if (!s) return s;
  const { id, captured_at, created_at, notes, photo_url, user_id, ...rest } = s;
  
  // Collect all numeric/measurement fields into measurements
  const measurements: Record<string, number> = {};
  for (const [k, v] of Object.entries(rest)) {
    if (typeof v === "number") {
      measurements[k] = v;
    }
  }
  
  return {
    id,
    created_at: captured_at || created_at,
    measurements,
    notes,
    photo_url,
    user_id,
  };
}

