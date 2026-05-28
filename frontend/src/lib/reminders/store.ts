/**
 * Reminders — client-side only.
 * The backend has no reminders endpoint, so we persist to localStorage.
 */
import * as React from "react";

export type Reminder = {
  id: string;
  title: string;
  time: string; // HH:MM
  days: number[]; // 0-6 (Sun-Sat)
  enabled: boolean;
  createdAt: number;
};

const KEY = "fit_reminders";

function read(): Reminder[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Reminder[]) : [];
  } catch {
    return [];
  }
}

function write(list: Reminder[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(list));
}

export function useReminders() {
  const [items, setItems] = React.useState<Reminder[]>([]);

  React.useEffect(() => {
    setItems(read());
  }, []);

  const persist = (next: Reminder[]) => {
    setItems(next);
    write(next);
  };

  return {
    items,
    add: (r: Omit<Reminder, "id" | "createdAt">) =>
      persist([{ ...r, id: crypto.randomUUID(), createdAt: Date.now() }, ...items]),
    update: (id: string, patch: Partial<Reminder>) =>
      persist(items.map((x) => (x.id === id ? { ...x, ...patch } : x))),
    remove: (id: string) => persist(items.filter((x) => x.id !== id)),
    toggle: (id: string) =>
      persist(items.map((x) => (x.id === id ? { ...x, enabled: !x.enabled } : x))),
  };
}
