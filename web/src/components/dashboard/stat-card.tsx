import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  sub,
  accent = false,
  tone,
}: {
  label: string;
  value: string;
  sub?: React.ReactNode;
  accent?: boolean;
  tone?: "success" | "warning" | "danger";
}) {
  const valueColor =
    tone === "success"
      ? "text-success"
      : tone === "warning"
        ? "text-warning"
        : tone === "danger"
          ? "text-danger"
          : "text-ink";
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border bg-surface p-5 shadow-[var(--shadow-card)]",
        accent ? "border-accent/30" : "border-border",
      )}
    >
      <div className="text-[12px] font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </div>
      <div className={cn("mt-2 text-[26px] font-semibold leading-none tnum", valueColor)}>
        {value}
      </div>
      {sub && <div className="mt-2.5 text-[13px] text-ink-muted">{sub}</div>}
    </div>
  );
}
