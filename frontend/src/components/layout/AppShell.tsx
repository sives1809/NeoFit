import * as React from "react";
import { Link, useLocation } from "@tanstack/react-router";
import { LayoutDashboard, Ruler, Salad, History, Bell, User, LogOut, Menu, X } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/store";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/measure", label: "Measure", icon: Ruler },
  { to: "/diet", label: "Diet", icon: Salad },
  { to: "/history", label: "History", icon: History },
  { to: "/reminders", label: "Reminders", icon: Bell },
  { to: "/profile", label: "Profile", icon: User },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(() => setMobileOpen(false), [location.pathname]);

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar — desktop */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-border/60 bg-sidebar/60 px-4 py-6 backdrop-blur-xl lg:flex lg:flex-col">
        <Logo className="px-2" />
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} active={location.pathname.startsWith(item.to)} />
          ))}
        </nav>
        <div className="glass rounded-xl p-3">
          <p className="truncate text-xs text-muted-foreground">Signed in as</p>
          <p className="truncate text-sm font-medium">{user?.email ?? user?.username ?? "—"}</p>
          <Button variant="ghost" size="sm" onClick={logout} className="mt-2 h-8 w-full justify-start text-muted-foreground hover:text-foreground">
            <LogOut className="mr-2 h-4 w-4" /> Sign out
          </Button>
        </div>
      </aside>

      {/* Mobile topbar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border/60 bg-background/70 px-4 py-3 backdrop-blur-xl lg:hidden">
        <Logo />
        <button
          aria-label="Open menu"
          onClick={() => setMobileOpen((v) => !v)}
          className="grid h-9 w-9 place-items-center rounded-md border border-border/60 bg-card/60"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-x-0 top-[57px] z-30 border-b border-border/60 bg-background/95 px-4 py-4 backdrop-blur-xl lg:hidden">
          <nav className="flex flex-col gap-1">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} active={location.pathname.startsWith(item.to)} />
            ))}
            <Button variant="ghost" onClick={logout} className="mt-2 justify-start text-muted-foreground">
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </Button>
          </nav>
        </div>
      ) : null}

      <main className="flex-1 px-4 py-6 pb-24 md:px-8 md:py-10 lg:pb-10">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-border/60 bg-background/85 px-2 py-2 backdrop-blur-xl lg:hidden">
        {NAV.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className={cn("h-5 w-5", active && "drop-shadow-[0_0_8px_oklch(0.88_0.24_150/0.7)]")} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function NavLink({ to, label, Icon, active }: { to: string; label: string; Icon: React.ComponentType<{ className?: string }>; active: boolean }) {
  return (
    <Link
      to={to}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
      )}
    >
      <Icon className={cn("h-4 w-4 transition", active && "drop-shadow-[0_0_8px_oklch(0.88_0.24_150/0.7)]")} />
      {label}
      {active ? <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_oklch(0.88_0.24_150/0.8)]" /> : null}
    </Link>
  );
}
