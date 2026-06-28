"use client";

import { Inbox, TriangleAlert } from "lucide-react";

export function EmptyState({
  title,
  hint,
  icon: Icon = Inbox,
}: {
  title: string;
  hint?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-soft">
        <Icon className="h-5 w-5 text-ink-subtle" />
      </div>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 max-w-xs text-[13px] text-ink-subtle">{hint}</p>}
    </div>
  );
}

export function ErrorState({
  title = "Couldn't load this",
  hint = "The API may be offline. Start it with `make dev-api`, then retry.",
  onRetry,
}: {
  title?: string;
  hint?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-danger-soft">
        <TriangleAlert className="h-5 w-5 text-danger" />
      </div>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-sm text-[13px] text-ink-subtle">{hint}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-hover"
        >
          Retry
        </button>
      )}
    </div>
  );
}
