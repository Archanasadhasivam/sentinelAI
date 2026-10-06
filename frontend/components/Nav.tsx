"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessagesSquare, Activity, Bell, Sliders, Settings, LogOut } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "./AuthProvider";

const LINKS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/playground", label: "Sandbox", icon: MessagesSquare },
  { href: "/monitor", label: "Monitor", icon: Activity },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/policy", label: "Policy", icon: Sliders },
  { href: "/settings", label: "Settings", icon: Settings },
];

/** The mark: a signal source with two rings of reach, standing in for a
 * watchtower beacon rather than a generic shield glyph. */
function BeaconMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="2.4" fill="hsl(var(--primary))" />
      <circle cx="11" cy="11" r="6" stroke="hsl(var(--primary))" strokeWidth="1.4" opacity="0.55" />
      <circle cx="11" cy="11" r="9.6" stroke="hsl(var(--primary))" strokeWidth="1.2" opacity="0.25" />
    </svg>
  );
}

export function Nav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <header className="fixed inset-y-0 left-0 z-20 w-[76px] md:w-[152px] border-r border-border bg-surface flex flex-col">
      <Link href="/" className="flex items-center gap-2 px-4 md:px-5 h-16 border-b border-border shrink-0">
        <BeaconMark />
        <span className="hidden md:inline display text-[17px] font-semibold tracking-wide leading-none pt-0.5">
          SENTINEL
        </span>
      </Link>

      <nav className="flex-1 flex flex-col gap-0.5 py-3 overflow-y-auto">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`relative flex flex-col md:flex-row items-center md:items-center gap-0.5 md:gap-2.5 px-2 md:px-5 py-2.5 text-[11px] md:text-sm transition-colors ${
                active ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span
                className={`absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full transition-opacity ${
                  active ? "bg-primary opacity-100" : "opacity-0"
                }`}
              />
              <Icon size={17} strokeWidth={active ? 2.25 : 1.75} />
              <span className="leading-none">{label}</span>
            </Link>
          );
        })}
      </nav>

      {user && (
        <div className="px-3 md:px-5 py-3 border-t border-border space-y-2">
          <p className="hidden md:block text-[11px] text-muted-foreground truncate" title={user.email}>
            {user.email}
          </p>
          <button
            onClick={logout}
            title="Log out"
            className="flex items-center gap-2 text-[11px] md:text-sm text-muted-foreground hover:text-foreground"
          >
            <LogOut size={16} strokeWidth={1.75} />
            <span className="hidden md:inline">Log out</span>
          </button>
        </div>
      )}

      <div className="p-3 border-t border-border flex justify-center md:justify-start">
        <ThemeToggle />
      </div>
    </header>
  );
}