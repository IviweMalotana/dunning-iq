import Link from "next/link";
import {
  ArrowRight,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Workflow,
  Brain,
  SlidersHorizontal,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import { formatMoney, formatPercent } from "@/lib/utils";
import { DashboardSummary } from "@/lib/types";
import { Architecture } from "@/components/landing/architecture";
import { MetricPlaceholder } from "@/components/landing/placeholder";

export const dynamic = "force-dynamic";

// Pull live numbers from the running demo, but never let the landing depend on it.
async function getLiveStats(): Promise<DashboardSummary | null> {
  try {
    return await apiGet<DashboardSummary>("/api/dashboard/summary", { revalidate: 30 });
  } catch {
    return null;
  }
}

export default async function CaseStudy() {
  const stats = await getLiveStats();

  return (
    <div className="bg-canvas text-ink">
      {/* Nav */}
      <header className="sticky top-0 z-20 border-b border-border bg-surface/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-[7px] bg-accent text-[13px] font-bold text-ink-invert">
              D
            </div>
            <span className="text-[15px] font-semibold tracking-tight">Dunning IQ</span>
          </div>
          <div className="flex items-center gap-4 text-[13px]">
            <a href="#architecture" className="hidden text-ink-muted hover:text-ink sm:block">
              Architecture
            </a>
            <a href="#outcomes" className="hidden text-ink-muted hover:text-ink sm:block">
              Outcomes
            </a>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 font-medium text-ink-invert transition-colors hover:bg-accent-hover"
            >
              Live demo <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 pb-14 pt-16 sm:pt-24">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-muted">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          AI-native billing recovery · case study
        </div>
        <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
          An AI agent that recovers failed recurring payments — and shows its work.
        </h1>
        <p className="mt-5 max-w-2xl text-[17px] leading-relaxed text-ink-muted">
          Dunning IQ ingests failed-payment events, classifies why each one failed, decides a
          retry strategy, drafts the customer message at the right tone, and knows when to escalate
          to a human. Every decision is logged with the agent&apos;s plain-English reasoning, so a
          billing operator can audit exactly why it did what it did.
        </p>
        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-ink-invert transition-colors hover:bg-accent-hover"
          >
            Open the live demo <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/queue"
            className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-surface-hover"
          >
            See the dunning queue
          </Link>
          <span className="text-[13px] text-ink-subtle">No login — seeded with realistic data.</span>
        </div>

        {/* Live demo glance */}
        {stats && (
          <div className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-[var(--radius-card)] border border-border bg-border sm:grid-cols-4">
            <Glance label="Recovered (demo)" value={formatMoney(stats.recovered_usd_minor, "USD", { compact: true })} />
            <Glance label="At risk now" value={formatMoney(stats.at_risk_usd_minor, "USD", { compact: true })} />
            <Glance label="Recovery rate" value={formatPercent(stats.recovery_rate)} />
            <Glance label="Cases tracked" value={String(stats.total_cases)} />
          </div>
        )}
      </section>

      {/* Problem */}
      <Section eyebrow="The problem" title="Failed payments quietly leak recurring revenue.">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <Point
            title="Involuntary churn is the silent killer"
            body="A large share of subscription cancellations aren't decisions — they're cards that expired or accounts that were short for a day. The revenue is recoverable, but only if you act fast and correctly."
          />
          <Point
            title="Manual dunning doesn't scale"
            body="Blanket retry schedules and generic 'your payment failed' emails treat an expired card the same as insufficient funds. Credit-control teams burn hours on cases that should never reach them."
          />
          <Point
            title="Black-box automation isn't trusted"
            body="Finance won't hand collections to a system it can't audit. If you can't see why a charge was retried or a customer was escalated, you can't sign off on it."
          />
        </div>
      </Section>

      {/* Approach */}
      <Section eyebrow="The approach" title="A specialist agent for each failed payment — with a guardrail spine.">
        <p className="-mt-2 mb-8 max-w-2xl text-[15px] leading-relaxed text-ink-muted">
          The LLM supplies judgment and prose; hard billing rules stay in code. The agent can be
          expressive without ever doing something a billing operator would veto — it can&apos;t
          retry a stolen card or sit on suspected fraud.
        </p>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Step icon={Workflow} step="01" title="Classify"
            body="Map the raw decline (insufficient funds, expired card, do-not-honor, fraud…) to what it means for recovery." />
          <Step icon={Brain} step="02" title="Plan & draft"
            body="Pick a retry cadence and backoff, then write the customer message at the right escalation tone." />
          <Step icon={ScrollText} step="03" title="Log the reasoning"
            body="Every retry, message, and escalation is stored with a timestamp and a plain-English justification." />
          <Step icon={ShieldCheck} step="04" title="Escalate safely"
            body="When automation is exhausted — or the case is high-risk — hand off to a human with full context." />
        </div>
      </Section>

      {/* Auditability highlight */}
      <Section eyebrow="Why it's different" title="The audit trail is the product.">
        <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-2">
          <div>
            <p className="text-[15px] leading-relaxed text-ink-muted">
              Most dunning tools give you a status. Dunning IQ gives you the reasoning behind every
              status. Each case is a timeline an operator can read top to bottom — what failed, how
              the agent classified it, why it chose that retry schedule, and the exact message it
              drafted — with a control to approve, edit, or override at any step.
            </p>
            <ul className="mt-5 space-y-2.5 text-[14px] text-ink-muted">
              {[
                "Plain-English reasoning on every decision",
                "Human-in-the-loop: approve, edit, or override",
                "Live policy editor — change the rules, watch the agent adapt",
              ].map((t) => (
                <li key={t} className="flex items-center gap-2.5">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success-soft">
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
            <Link
              href="/queue"
              className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent-ink hover:underline"
            >
              Open a case and read the timeline <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {/* Mock reasoning snippet */}
          <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-2 text-[13px] font-medium text-ink">
              <Sparkles className="h-3.5 w-3.5 text-accent" /> Agent · classified as Insufficient funds
            </div>
            <div className="mt-2 rounded-md border-l-2 border-accent/40 bg-surface-subtle px-3 py-2 text-[13px] leading-relaxed text-ink-muted">
              Processor returned <code className="rounded bg-neutral-soft px-1 font-mono text-[12px]">insufficient_funds</code>. This
              is the single most recoverable decline — the card is valid, the account is simply short
              right now. Scheduling 4 retries (+2d, +3d, +5d, +7d); the widening gaps straddle a
              likely pay date.
            </div>
            <div className="mt-2 text-xs text-ink-subtle">96% confidence · decided by Kimi</div>
          </div>
        </div>
      </Section>

      {/* Architecture */}
      <Section id="architecture" eyebrow="The architecture" title="Webhooks in, audited decisions out.">
        <Architecture />
      </Section>

      {/* Outcomes (placeholders) */}
      <Section id="outcomes" eyebrow="The outcome" title="Built on results from running live billing.">
        <p className="-mt-2 mb-8 max-w-2xl text-[15px] leading-relaxed text-ink-muted">
          Dunning IQ is the AI-native version of a production direct-debit failure system and
          credit-control funnel I built at a fintech. The figures below are{" "}
          <span className="font-medium text-ink">placeholders</span> — replace them with your own
          verified numbers.
        </p>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <MetricPlaceholder
            label="Billing capacity"
            suggested="≈ 7×"
            description="Increase in billing throughput after the failure-handling and credit-control redesign."
          />
          <MetricPlaceholder
            label="Bad debt recovered"
            suggested="$ —"
            description="Revenue reclaimed that would otherwise have been written off as involuntary churn."
          />
          <MetricPlaceholder
            label="Operator time saved"
            suggested="— %"
            description="Reduction in manual credit-control effort once the agent handled the routine cases."
          />
        </div>
      </Section>

      {/* CTA + footer */}
      <section className="mx-auto max-w-5xl px-6 pb-20">
        <div className="overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface p-8 text-center shadow-[var(--shadow-card)] sm:p-12">
          <h2 className="text-2xl font-semibold tracking-tight">See the agent work a live queue.</h2>
          <p className="mx-auto mt-2 max-w-xl text-[15px] text-ink-muted">
            The demo is seeded with hundreds of realistic accounts — recovered, escalated, and
            in-progress — so every screen is fully clickable.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-ink-invert transition-colors hover:bg-accent-hover"
            >
              Open the live demo <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/settings"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-surface-hover"
            >
              <SlidersHorizontal className="h-4 w-4" /> Tune the policy
            </Link>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-subtle">
          <span>Dunning IQ — portfolio case study.</span>
          <span className="flex flex-wrap gap-x-3 gap-y-1">
            <span>Next.js 15</span>
            <span>FastAPI</span>
            <span>Postgres</span>
            <span>Kimi (Moonshot)</span>
          </span>
        </div>
      </section>
    </div>
  );
}

function Glance({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface p-4">
      <div className="text-[11px] font-medium uppercase tracking-wide text-ink-subtle">{label}</div>
      <div className="mt-1 text-xl font-semibold text-ink tnum">{value}</div>
    </div>
  );
}

function Section({
  id,
  eyebrow,
  title,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="border-t border-border">
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="text-[12px] font-semibold uppercase tracking-wider text-accent-ink">
          {eyebrow}
        </div>
        <h2 className="mt-2 max-w-3xl text-2xl font-semibold tracking-tight sm:text-3xl">
          {title}
        </h2>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

function Point({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-card)]">
      <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">{body}</p>
    </div>
  );
}

function Step({
  icon: Icon,
  step,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  step: string;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-soft">
          <Icon className="h-4 w-4 text-accent-ink" />
        </div>
        <span className="font-mono text-xs text-ink-subtle">{step}</span>
      </div>
      <h3 className="mt-3 text-[15px] font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink-muted">{body}</p>
    </div>
  );
}
