import * as React from "react";
import { cn } from "@/lib/utils";

export const GlassCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("glass rounded-2xl p-6", className)} {...props} />
  ),
);
GlassCard.displayName = "GlassCard";

export function StatTile({
  label,
  value,
  unit,
  hint,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <div className={cn("glass rounded-xl p-4", accent && "neon-glow")}>
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 font-mono-data text-2xl font-semibold tabular-nums text-foreground">
        {value}
        {unit ? <span className="ml-1 text-sm text-muted-foreground">{unit}</span> : null}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="glass flex flex-col items-center justify-center rounded-2xl p-10 text-center">
      <div className="mb-3 h-10 w-10 rounded-full border border-primary/30 bg-primary/10" />
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {description ? <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
