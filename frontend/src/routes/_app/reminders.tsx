import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Plus, Trash2, Bell } from "lucide-react";
import { GlassCard, SectionHeader, EmptyState } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useReminders } from "@/lib/reminders/store";

const DAYS = ["S", "M", "T", "W", "T", "F", "S"];

export const Route = createFileRoute("/_app/reminders")({
  component: RemindersPage,
});

function RemindersPage() {
  const { items, add, remove, toggle, update } = useReminders();
  const [title, setTitle] = React.useState("");
  const [time, setTime] = React.useState("08:00");
  const [days, setDays] = React.useState<number[]>([1, 2, 3, 4, 5]);

  const create = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    add({ title: title.trim(), time, days, enabled: true });
    setTitle("");
  };

  return (
    <div>
      <SectionHeader
        title="Reminders"
        subtitle="Local reminders, stored on this device."
      />

      <GlassCard className="mb-6">
        <form onSubmit={create} className="grid gap-3 md:grid-cols-[2fr_1fr_auto] md:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="r-title">What</Label>
            <Input id="r-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Log measurement, drink water…" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="r-time">When</Label>
            <Input id="r-time" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          </div>
          <Button type="submit" className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Plus className="mr-1.5 h-4 w-4" /> Add
          </Button>
        </form>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">Repeat</span>
          {DAYS.map((d, i) => {
            const on = days.includes(i);
            return (
              <button
                key={i}
                type="button"
                onClick={() => setDays(on ? days.filter((x) => x !== i) : [...days, i])}
                className={`grid h-7 w-7 place-items-center rounded-full border text-xs ${on ? "border-primary bg-primary/15 text-primary" : "border-border/60 text-muted-foreground"}`}
              >{d}</button>
            );
          })}
        </div>
      </GlassCard>

      {items.length === 0 ? (
        <EmptyState title="No reminders" description="Add a reminder above to keep your routine sharp." />
      ) : (
        <div className="grid gap-2">
          {items.map((r) => (
            <div key={r.id} className="glass flex items-center justify-between rounded-xl px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="grid h-9 w-9 place-items-center rounded-lg border border-primary/30 bg-primary/10"><Bell className="h-4 w-4 text-primary" /></div>
                <div>
                  <p className="font-medium">{r.title}</p>
                  <p className="font-mono-data text-xs text-muted-foreground">
                    {r.time} · {r.days.length === 7 ? "Every day" : r.days.map((d) => DAYS[d]).join(" ")}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Switch checked={r.enabled} onCheckedChange={() => toggle(r.id)} />
                <Button size="sm" variant="ghost" onClick={() => remove(r.id)} className="text-destructive hover:text-destructive">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* keep update referenced for future inline edit */}
      <span className="hidden">{String(!!update)}</span>
    </div>
  );
}
