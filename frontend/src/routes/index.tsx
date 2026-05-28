import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Activity, Camera, Salad, History, Sparkles, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { GlassCard, StatTile } from "@/components/brand/GlassCard";

export const Route = createFileRoute("/")({
  component: Landing,
});

function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-50" />

      {/* Nav */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo />
        <nav className="hidden gap-8 text-sm text-muted-foreground md:flex">
          <a href="#features" className="hover:text-foreground">Features</a>
          <a href="#how" className="hover:text-foreground">How it works</a>
          <a href="#stack" className="hover:text-foreground">Tech</a>
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">Sign in</Link>
          </Button>
          <Button asChild size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Link to="/signup">Get started</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 pt-12 pb-20 md:pt-24">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs uppercase tracking-wider text-primary">
            <Sparkles className="h-3.5 w-3.5" /> AI fitness — final year project
          </div>
          <h1 className="mt-6 font-display text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
            Your body, <span className="neon-text">measured by AI</span>,
            <br className="hidden md:inline" /> coached by data.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-muted-foreground md:text-lg">
            NeonFit turns your webcam into a precision body-measurement studio.
            Pose-driven measurements, adaptive diet plans, and predictive insights —
            all in one futuristic dashboard.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg" className="bg-primary text-primary-foreground hover:bg-primary/90 neon-glow">
              <Link to="/signup">
                Launch dashboard <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="border border-border/60">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>

        {/* Hero preview */}
        <div className="relative mx-auto mt-16 max-w-4xl">
          <div className="absolute -inset-6 bg-primary/20 blur-3xl opacity-40" aria-hidden />
          <GlassCard className="relative grid gap-4 p-6 md:grid-cols-4 md:p-8">
            <StatTile label="Shoulder Width" value="52.4" unit="cm" hint="+0.8 vs last" accent />
            <StatTile label="Arm Girth" value="38.1" unit="cm" hint="+1.2 vs last" />
            <StatTile label="Thigh Girth" value="62.3" unit="cm" />
            <StatTile label="Confidence" value="0.94" hint="High Tracking Accuracy" />
            <div className="glass col-span-2 rounded-xl p-4">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Today's plan</p>
              <p className="mt-2 font-mono-data text-xl tabular-nums">2,180 kcal · 168g P · 220g C · 70g F</p>
              <p className="mt-1 text-xs text-muted-foreground">Adaptive to your last 7 sessions</p>
            </div>
            <div className="glass col-span-2 rounded-xl p-4">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Growth Trends</p>
              <p className="mt-2 font-mono-data text-xl tabular-nums">+1.2cm Arm Girth in 6 weeks</p>
              <p className="mt-1 text-xs text-muted-foreground">Based on current trajectory</p>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
        <div className="grid gap-4 md:grid-cols-3">
          <Feature
            icon={<Camera className="h-5 w-5 text-primary" />}
            title="Pose-driven measurement"
            body="Capture shoulder width, arm girth, and thigh girth from a single webcam frame. MediaPipe-ready pipeline."
          />
          <Feature
            icon={<Salad className="h-5 w-5 text-primary" />}
            title="Adaptive diet"
            body="Macros and meals that recompute as your body and goals change."
          />
          <Feature
            icon={<Activity className="h-5 w-5 text-primary" />}
            title="Predictive insights"
            body="See where you're headed, not just where you are. Trend models built in."
          />
          <Feature
            icon={<History className="h-5 w-5 text-primary" />}
            title="Full session history"
            body="Every measurement is saved. Review, compare, and export anytime."
          />
          <Feature
            icon={<ShieldCheck className="h-5 w-5 text-primary" />}
            title="Local-first camera"
            body="Frames never leave your device — only landmark coordinates reach the server."
          />
          <Feature
            icon={<Sparkles className="h-5 w-5 text-primary" />}
            title="Built for builders"
            body="Clean API surface, swappable auth adapter, ready for production."
          />
        </div>
      </section>

      <footer className="relative z-10 border-t border-border/40 py-8 text-center text-xs text-muted-foreground">
        Built with TanStack Start · React · Tailwind · FastAPI
      </footer>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <GlassCard className="transition hover:border-primary/40">
      <div className="mb-3 grid h-9 w-9 place-items-center rounded-lg border border-primary/30 bg-primary/10">
        {icon}
      </div>
      <h3 className="font-display text-base font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{body}</p>
    </GlassCard>
  );
}
