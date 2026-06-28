import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-md", className)} />;
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-card)]">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-7 w-32" />
      <Skeleton className="mt-3 h-3 w-20" />
    </div>
  );
}

export function TableRowSkeleton({ cols = 6 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 border-b border-border px-5 py-3.5">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className={cn("h-3", i === 0 ? "w-40" : "w-20 flex-1")} />
      ))}
    </div>
  );
}
