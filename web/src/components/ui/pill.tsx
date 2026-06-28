import { cn } from "@/lib/utils";
import { CaseStatus, STATUS_META } from "@/lib/types";

type Tone = "success" | "info" | "warning" | "danger" | "neutral" | "accent";

const TONE: Record<Tone, string> = {
  success: "bg-success-soft text-success",
  info: "bg-info-soft text-info",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  neutral: "bg-neutral-soft text-neutral",
  accent: "bg-accent-soft text-accent-ink",
};

export function Pill({
  tone = "neutral",
  children,
  dot = false,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        TONE[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />}
      {children}
    </span>
  );
}

export function StatusPill({ status }: { status: CaseStatus }) {
  const meta = STATUS_META[status];
  return (
    <Pill tone={meta.tone} dot>
      {meta.label}
    </Pill>
  );
}
