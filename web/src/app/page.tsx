import Link from "next/link";

/**
 * Temporary holding page for M0 (scaffold). The real `/` case-study landing
 * ships in M6; the operator dashboard lives under /dashboard from M4.
 */
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <div className="inline-flex w-fit items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
        Scaffold ready · M0
      </div>

      <h1 className="mt-6 text-3xl font-semibold tracking-tight text-ink">
        Dunning IQ
      </h1>
      <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
        An AI agent that handles failed recurring payments end to end — it
        classifies why a payment failed, decides the retry strategy, drafts the
        customer message at the right tone, and logs every decision with
        plain-English reasoning a human can audit.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {[
          ["Recovery dashboard", "At-risk vs recovered revenue, recovery rate, breakdown by reason."],
          ["Dunning queue", "Every account in dunning with its current step and next action."],
          ["Case detail", "A timeline of decisions, the agent's reasoning, drafted messages."],
          ["Policy editor", "Tune retry rules and message tone, watch the agent adapt."],
        ].map(([title, body]) => (
          <div
            key={title}
            className="rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
          >
            <div className="text-sm font-medium text-ink">{title}</div>
            <div className="mt-1 text-[13px] leading-relaxed text-ink-subtle">
              {body}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 flex items-center gap-3">
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-md bg-accent px-3.5 py-2 text-sm font-medium text-ink-invert transition-colors hover:bg-accent-hover"
        >
          Open the dashboard
        </Link>
        <span className="text-xs text-ink-subtle">Wired up in milestone 4</span>
      </div>
    </main>
  );
}
