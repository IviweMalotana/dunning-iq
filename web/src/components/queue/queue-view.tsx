"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Search, Sparkles, UserRound } from "lucide-react";
import { swrFetcher } from "@/lib/api";
import { cn, formatMoney, isLiveLLM } from "@/lib/utils";
import { QueuePage } from "@/lib/types";
import { StatusPill } from "@/components/ui/pill";
import { ErrorState, EmptyState } from "@/components/ui/states";
import { TableRowSkeleton } from "@/components/ui/skeleton";

const TABS: { key: string; label: string }[] = [
  { key: "open", label: "Open" },
  { key: "in_progress", label: "In progress" },
  { key: "escalated", label: "Escalated" },
  { key: "recovered", label: "Recovered" },
  { key: "written_off", label: "Written off" },
  { key: "paused", label: "Paused" },
  { key: "all", label: "All" },
];

const SORTS = [
  { key: "next", label: "Next action" },
  { key: "amount", label: "Amount at risk" },
  { key: "opened", label: "Most recent" },
];

function relTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = new Date(iso).getTime() - Date.now();
  const past = diff < 0;
  const mins = Math.round(Math.abs(diff) / 60000);
  const fmt =
    mins < 60 ? `${mins}m` : mins < 1440 ? `${Math.round(mins / 60)}h` : `${Math.round(mins / 1440)}d`;
  if (fmt === "0m") return "now";
  return past ? `${fmt} ago` : `in ${fmt}`;
}

export function QueueView() {
  const router = useRouter();
  const [tab, setTab] = useState("open");
  const [sort, setSort] = useState("next");
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search, 250);

  const key = `/api/cases?status=${tab}&sort=${sort}${
    debounced ? `&search=${encodeURIComponent(debounced)}` : ""
  }`;
  const { data, error, isLoading } = useSWR<QueuePage>(key, swrFetcher, {
    keepPreviousData: true,
    refreshInterval: 20000,
  });

  const counts = data?.counts_by_status ?? {};
  const openCount =
    (counts.in_progress ?? 0) + (counts.escalated ?? 0) + (counts.paused ?? 0);

  return (
    <div className="p-6">
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface shadow-[var(--shadow-card)]">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
          <div className="flex flex-wrap gap-1">
            {TABS.map((t) => {
              const c = t.key === "open" ? openCount : t.key === "all" ? undefined : counts[t.key];
              return (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-[13px] font-medium transition-colors",
                    tab === t.key
                      ? "bg-accent-soft text-accent-ink"
                      : "text-ink-muted hover:bg-surface-hover hover:text-ink",
                  )}
                >
                  {t.label}
                  {c != null && (
                    <span className="ml-1.5 text-ink-subtle tnum">{c}</span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search customer…"
                className="w-44 rounded-md border border-border bg-surface py-1.5 pl-8 pr-2 text-[13px] text-ink outline-none transition-colors placeholder:text-ink-subtle focus:border-accent"
              />
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="rounded-md border border-border bg-surface px-2 py-1.5 text-[13px] text-ink-muted outline-none focus:border-accent"
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  Sort: {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Header row */}
        <div className="hidden grid-cols-[minmax(0,2.2fr)_1fr_1.3fr_1fr_1.4fr_1fr] items-center gap-4 border-b border-border bg-surface-subtle px-5 py-2 text-[11px] font-semibold uppercase tracking-wide text-ink-subtle md:grid">
          <div>Customer</div>
          <div className="text-right">At risk</div>
          <div>Failure reason</div>
          <div>Step</div>
          <div>Next action</div>
          <div className="text-right">Status</div>
        </div>

        {/* Body */}
        {error ? (
          <ErrorState />
        ) : isLoading && !data ? (
          <div>{Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} />)}</div>
        ) : data && data.items.length === 0 ? (
          <EmptyState
            title="No cases here"
            hint="Nothing matches this filter. Fire some events with `make simulate` to populate the queue."
          />
        ) : (
          <div className="divide-y divide-border">
            {data?.items.map((c) => (
              <button
                key={c.id}
                onClick={() => router.push(`/cases/${c.id}`)}
                className="grid w-full grid-cols-1 gap-1 px-5 py-3 text-left transition-colors hover:bg-surface-hover md:grid-cols-[minmax(0,2.2fr)_1fr_1.3fr_1fr_1.4fr_1fr] md:items-center md:gap-4"
              >
                {/* Customer */}
                <div className="flex min-w-0 items-center gap-2.5">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-neutral-soft">
                    <UserRound className="h-3.5 w-3.5 text-ink-subtle" />
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-medium text-ink">
                      {c.customer_name}
                    </div>
                    <div className="truncate text-xs text-ink-subtle">
                      {c.company ?? c.email}
                    </div>
                  </div>
                </div>
                {/* Amount */}
                <div className="md:text-right">
                  <span className="text-[13px] font-semibold text-ink tnum">
                    {formatMoney(c.amount_minor, c.currency)}
                  </span>
                  {c.currency !== "USD" && (
                    <span className="ml-1 text-xs text-ink-subtle tnum">
                      ≈{formatMoney(c.amount_usd_minor, "USD")}
                    </span>
                  )}
                </div>
                {/* Reason */}
                <div className="flex items-center gap-1.5 text-[13px] text-ink-muted">
                  {c.failure_label}
                  {isLiveLLM(c.decided_by) && (
                    <Sparkles className="h-3 w-3 text-accent" />
                  )}
                </div>
                {/* Step */}
                <div className="flex items-center gap-2">
                  <div className="flex gap-0.5">
                    {Array.from({ length: Math.max(c.total_steps, 1) }).map((_, i) => (
                      <span
                        key={i}
                        className={cn(
                          "h-1.5 w-3 rounded-full",
                          i < c.current_step ? "bg-accent" : "bg-neutral-soft",
                        )}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-ink-subtle tnum">
                    {c.current_step}/{c.total_steps}
                  </span>
                </div>
                {/* Next action */}
                <div className="min-w-0 text-[13px] text-ink-muted">
                  <span className="truncate">{c.next_action_label ?? "—"}</span>
                  {c.next_action_at && (
                    <span className="ml-1 text-xs text-ink-subtle">
                      · {relTime(c.next_action_at)}
                    </span>
                  )}
                </div>
                {/* Status */}
                <div className="md:text-right">
                  <StatusPill status={c.status} />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function useDebounce<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}
