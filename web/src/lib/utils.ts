import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with conflict resolution. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format minor-unit money (cents) as a currency string. */
export function formatMoney(
  amountMinor: number,
  currency = "USD",
  opts: { compact?: boolean } = {},
) {
  const value = amountMinor / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: opts.compact ? "compact" : "standard",
    maximumFractionDigits: opts.compact ? 1 : 2,
  }).format(value);
}

/** Percentage with one decimal, e.g. 0.732 -> "73.2%". */
export function formatPercent(ratio: number, digits = 1) {
  return `${(ratio * 100).toFixed(digits)}%`;
}

/** Relative time like "2h ago", "3d ago". */
export function timeAgo(iso: string, now: Date = new Date()) {
  const then = new Date(iso).getTime();
  const diff = Math.max(0, now.getTime() - then);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

/** Absolute, readable date-time. */
export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
