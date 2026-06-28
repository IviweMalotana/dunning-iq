import { cn } from "@/lib/utils";

/**
 * A clearly-marked placeholder for a real metric the owner will fill in.
 * The dashed border + tag make it unmistakable that the figure is illustrative.
 */
export function MetricPlaceholder({
  label,
  suggested,
  description,
  className,
}: {
  label: string;
  suggested: string;
  description: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative rounded-[var(--radius-card)] border border-dashed border-accent/40 bg-accent-soft/40 p-5",
        className,
      )}
    >
      <span className="absolute right-3 top-3 rounded-full bg-surface px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent-ink ring-1 ring-accent/30">
        Your metric
      </span>
      <div className="text-[12px] font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </div>
      <div className="mt-2 text-[28px] font-semibold leading-none text-accent-ink tnum">
        {suggested}
      </div>
      <p className="mt-2.5 text-[13px] leading-relaxed text-ink-muted">{description}</p>
    </div>
  );
}
