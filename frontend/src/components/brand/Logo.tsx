import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative h-7 w-7">
        <div className="absolute inset-0 rounded-md bg-primary/20 blur-md" aria-hidden />
        <div className="relative grid h-7 w-7 place-items-center rounded-md border border-primary/40 bg-primary/10">
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-primary" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 12h3l2-6 4 12 2-6h5" />
          </svg>
        </div>
      </div>
      <span className="font-display text-base font-semibold tracking-tight">
        Neon<span className="text-primary">Fit</span>
      </span>
    </div>
  );
}
