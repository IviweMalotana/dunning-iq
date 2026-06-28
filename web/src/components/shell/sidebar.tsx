"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ListChecks, Settings, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Recovery", icon: LayoutDashboard },
  { href: "/queue", label: "Dunning queue", icon: ListChecks },
  { href: "/settings", label: "Policy & tone", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface lg:flex">
      <div className="flex h-14 items-center gap-2.5 px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-accent text-[13px] font-bold text-ink-invert">
          D
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-ink">
          Dunning&nbsp;IQ
        </span>
      </div>

      <nav className="flex-1 px-3 py-3">
        <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
          Operations
        </p>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "mt-0.5 flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] font-medium transition-colors",
                active
                  ? "bg-accent-soft text-accent-ink"
                  : "text-ink-muted hover:bg-surface-hover hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] font-medium text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
        >
          <BookOpen className="h-4 w-4 shrink-0" />
          Case study
        </Link>
      </div>
    </aside>
  );
}
