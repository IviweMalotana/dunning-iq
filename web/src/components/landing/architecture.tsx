import { ArrowRight, Webhook, ServerCog, Database, MonitorSmartphone } from "lucide-react";

const STAGES = [
  {
    icon: Webhook,
    title: "Ingest",
    tech: "Stripe / Paddle webhooks · simulator",
    body: "Signed payment-failed events arrive (or are simulated) and are normalised.",
  },
  {
    icon: ServerCog,
    title: "Decide",
    tech: "FastAPI · Claude (Anthropic SDK)",
    body: "The agent classifies the failure, plans retries, drafts the message, and logs its reasoning.",
  },
  {
    icon: Database,
    title: "Record",
    tech: "Postgres · SQLAlchemy + Alembic",
    body: "Cases, events, and messages persist — every decision with its plain-English justification.",
  },
  {
    icon: MonitorSmartphone,
    title: "Operate",
    tech: "Next.js · Recharts (Vercel)",
    body: "Operators watch recovery, work the queue, and approve, edit, or override the agent.",
  },
];

export function Architecture() {
  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-card)] sm:p-7">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] md:items-stretch md:gap-2">
        {STAGES.map((s, i) => (
          <div key={s.title} className="contents">
            <div className="rounded-lg border border-border bg-surface-subtle p-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-soft">
                <s.icon className="h-4 w-4 text-accent-ink" />
              </div>
              <div className="mt-3 text-sm font-semibold text-ink">
                {i + 1}. {s.title}
              </div>
              <div className="mt-0.5 font-mono text-[11px] text-ink-subtle">{s.tech}</div>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-muted">{s.body}</p>
            </div>
            {i < STAGES.length - 1 && (
              <div className="flex items-center justify-center text-ink-subtle">
                <ArrowRight className="hidden h-4 w-4 md:block" />
                <ArrowRight className="h-4 w-4 rotate-90 md:hidden" />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-1.5 border-t border-border pt-4 text-xs text-ink-subtle">
        <span className="font-medium text-ink-muted">Deployed on</span>
        <span>Vercel — web</span>
        <span>Railway — API + Postgres</span>
        <span className="ml-auto">
          Demo runs offline on SQLite with a deterministic agent fallback.
        </span>
      </div>
    </div>
  );
}
