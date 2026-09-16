"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, LayoutDashboard, MessagesSquare, Activity, Bell, Sliders, Settings } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/playground", label: "Playground", icon: MessagesSquare },
  { href: "/monitor", label: "Monitor", icon: Activity },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/policy", label: "Policy", icon: Sliders },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-surface sticky top-0 z-20">
      <div className="mx-auto max-w-7xl flex items-center gap-6 px-4 h-14">
        <Link href="/" className="flex items-center gap-2 font-semibold shrink-0">
          <ShieldCheck size={20} className="text-primary" />
          SentinelAI
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm whitespace-nowrap transition-colors ${
                  active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-surface-hover"
                }`}
              >
                <Icon size={14} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
