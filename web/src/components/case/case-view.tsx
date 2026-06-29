"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  Ban,
  CalendarClock,
  CheckCircle2,
  Cog,
  Mail,
  PenLine,
  RefreshCw,
  Send,
  Sparkles,
  UserRound,
  XCircle,
} from "lucide-react";
import { apiSend, swrFetcher } from "@/lib/api";
import { cn, decidedByLabel, formatDateTime, formatMoney, isLiveLLM, timeAgo } from "@/lib/utils";
import { CaseDetail, CaseEvent, CaseMessage } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Pill, StatusPill } from "@/components/ui/pill";
import { ErrorState } from "@/components/ui/states";
import { Skeleton } from "@/components/ui/skeleton";

const EVENT_ICON: Record<string, { icon: React.ComponentType<{ className?: string }>; tone: string }> = {
  case_opened: { icon: AlertCircle, tone: "text-danger bg-danger-soft" },
  classification: { icon: Sparkles, tone: "text-accent-ink bg-accent-soft" },
  retry_scheduled: { icon: CalendarClock, tone: "text-info bg-info-soft" },
  retry_attempted: { icon: RefreshCw, tone: "text-ink-muted bg-neutral-soft" },
  retry_failed: { icon: XCircle, tone: "text-danger bg-danger-soft" },
  retry_succeeded: { icon: CheckCircle2, tone: "text-success bg-success-soft" },
  message_drafted: { icon: PenLine, tone: "text-accent-ink bg-accent-soft" },
  message_sent: { icon: Send, tone: "text-info bg-info-soft" },
  escalated: { icon: ArrowUpRight, tone: "text-warning bg-warning-soft" },
  human_review: { icon: UserRound, tone: "text-ink-muted bg-neutral-soft" },
  resolved: { icon: CheckCircle2, tone: "text-success bg-success-soft" },
  written_off: { icon: Ban, tone: "text-danger bg-danger-soft" },
  note: { icon: PenLine, tone: "text-ink-muted bg-neutral-soft" },
};

const ACTOR_LABEL: Record<string, string> = { agent: "Agent", human: "Operator", system: "System" };

export function CaseView({ id }: { id: string }) {
  const { data, error, isLoading, mutate } = useSWR<CaseDetail>(
    `/api/cases/${id}`,
    swrFetcher,
  );

  if (error) return <div className="p-6"><ErrorState /></div>;
  if (isLoading || !data) return <CaseSkeleton />;

  const c = data;
  const terminal = c.status === "recovered" || c.status === "written_off";

  async function override(action: string) {
    await apiSend(`/api/cases/${id}/override`, "POST", { action });
    mutate();
  }

  return (
    <div className="p-6">
      <Link
        href="/queue"
        className="mb-4 inline-flex items-center gap-1.5 text-[13px] text-ink-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to queue
      </Link>

      {/* Summary header */}
      <Card className="mb-5">
        <div className="flex flex-wrap items-start justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-neutral-soft">
              <UserRound className="h-5 w-5 text-ink-subtle" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-semibold tracking-tight text-ink">
                  {c.customer_name}
                </h2>
                <StatusPill status={c.status} />
              </div>
              <div className="mt-0.5 text-[13px] text-ink-muted">
                {c.company ? `${c.company} · ` : ""}
                {c.email}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-muted">
                <span>
                  <span className="text-ink-subtle">At risk </span>
                  <span className="font-semibold text-ink tnum">
                    {formatMoney(c.amount_minor, c.currency)}
                  </span>
                </span>
                <span>
                  <span className="text-ink-subtle">Plan </span>
                  {c.plan_name ?? "—"}
                </span>
                <span>
                  <span className="text-ink-subtle">Opened </span>
                  {timeAgo(c.opened_at)}
                </span>
              </div>
            </div>
          </div>

          {/* Override controls */}
          <div className="flex flex-wrap items-center gap-2">
            {terminal ? (
              <Pill tone="neutral">Case closed</Pill>
            ) : (
              <>
                {c.status === "paused" ? (
                  <OverrideButton onClick={() => override("resume")}>Resume</OverrideButton>
                ) : (
                  <OverrideButton onClick={() => override("pause")}>Pause</OverrideButton>
                )}
                {c.status !== "escalated" && (
                  <OverrideButton onClick={() => override("escalate")}>Escalate</OverrideButton>
                )}
                <OverrideButton primary onClick={() => override("resolve")}>
                  Mark recovered
                </OverrideButton>
                <OverrideButton danger onClick={() => override("write_off")}>
                  Write off
                </OverrideButton>
              </>
            )}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Timeline */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Decision timeline"
            subtitle="Every action the agent took, and exactly why."
          />
          <Timeline events={c.events} />
        </Card>

        {/* Right rail */}
        <div className="space-y-5">
          <PlanCard c={c} />
          <MessagesCard caseId={id} messages={c.messages} onChange={() => mutate()} />
        </div>
      </div>
    </div>
  );
}

function OverrideButton({
  children,
  onClick,
  primary,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  primary?: boolean;
  danger?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await onClick();
        } finally {
          setBusy(false);
        }
      }}
      className={cn(
        "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors disabled:opacity-50",
        primary
          ? "bg-accent text-ink-invert hover:bg-accent-hover"
          : danger
            ? "border border-border text-danger hover:bg-danger-soft"
            : "border border-border text-ink hover:bg-surface-hover",
      )}
    >
      {children}
    </button>
  );
}

function Timeline({ events }: { events: CaseEvent[] }) {
  if (events.length === 0)
    return <div className="px-5 py-10 text-center text-sm text-ink-subtle">No events yet.</div>;
  return (
    <ol className="px-5 py-4">
      {events.map((e, i) => {
        const meta = EVENT_ICON[e.type] ?? EVENT_ICON.note;
        const Icon = meta.icon;
        const last = i === events.length - 1;
        return (
          <li key={e.id} className="relative flex gap-3.5 pb-5 last:pb-0">
            {!last && (
              <span className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-border" />
            )}
            <div className={cn("z-0 flex h-8 w-8 shrink-0 items-center justify-center rounded-full", meta.tone)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-[13px] font-medium text-ink">{e.title}</span>
                <ActorBadge actor={e.actor} />
                <span className="text-xs text-ink-subtle">{formatDateTime(e.occurred_at)}</span>
              </div>
              {e.reasoning && (
                <div className="mt-1.5 rounded-md border-l-2 border-accent/40 bg-surface-subtle px-3 py-2 text-[13px] leading-relaxed text-ink-muted">
                  {renderReasoning(e.reasoning)}
                </div>
              )}
              {e.detail?.confidence != null && (
                <div className="mt-1.5 text-xs text-ink-subtle">
                  Confidence {Math.round((e.detail.confidence as number) * 100)}%
                  {e.detail.source ? ` · decided by ${e.detail.source}` : ""}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function ActorBadge({ actor }: { actor: string }) {
  const Icon = actor === "agent" ? Sparkles : actor === "human" ? UserRound : Cog;
  const tone = actor === "agent" ? "accent" : actor === "human" ? "info" : "neutral";
  return (
    <Pill tone={tone as never} className="px-1.5 py-0">
      <Icon className="h-2.5 w-2.5" />
      {ACTOR_LABEL[actor] ?? actor}
    </Pill>
  );
}

// Render **bold** spans and `code` from the reasoning markdown-lite.
function renderReasoning(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={i} className="font-semibold text-ink">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return (
        <code key={i} className="rounded bg-neutral-soft px-1 py-0.5 font-mono text-[12px] text-ink">
          {p.slice(1, -1)}
        </code>
      );
    return <span key={i}>{p}</span>;
  });
}

function PlanCard({ c }: { c: CaseDetail }) {
  const plan = (c.plan ?? {}) as Record<string, unknown>;
  const backoff = (plan.backoff_days as number[]) ?? [];
  return (
    <Card>
      <CardHeader title="Agent plan" subtitle={c.summary ?? undefined} />
      <dl className="divide-y divide-border text-[13px]">
        <Row label="Failure reason" value={c.failure_label} />
        <Row
          label="Classification"
          value={
            c.confidence != null
              ? `${Math.round(c.confidence * 100)}% confidence`
              : "—"
          }
        />
        <Row label="Decided by" value={
          <Pill tone={isLiveLLM(c.decided_by) ? "accent" : "neutral"} className="px-1.5 py-0">
            {decidedByLabel(c.decided_by)}
          </Pill>
        } />
        <Row
          label="Retry schedule"
          value={backoff.length ? backoff.map((d) => `+${d}d`).join(", ") : "No retries"}
        />
        <Row label="Step" value={`${c.current_step} of ${c.total_steps}`} />
        {c.escalated_to && (
          <Row label="Escalated to" value={c.escalated_to.replace("_", " ")} />
        )}
        {c.recovered_minor > 0 && (
          <Row
            label="Recovered"
            value={
              <span className="font-semibold text-success tnum">
                {formatMoney(c.recovered_minor, c.currency)}
              </span>
            }
          />
        )}
      </dl>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-5 py-2.5">
      <dt className="text-ink-subtle">{label}</dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

function MessagesCard({
  caseId,
  messages,
  onChange,
}: {
  caseId: string;
  messages: CaseMessage[];
  onChange: () => void;
}) {
  return (
    <Card>
      <CardHeader title="Customer messages" subtitle={`${messages.length} drafted`} />
      {messages.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-ink-subtle">No messages yet.</div>
      ) : (
        <div className="divide-y divide-border">
          {messages.map((m) => (
            <MessageRow key={m.id} caseId={caseId} m={m} onChange={onChange} />
          ))}
        </div>
      )}
    </Card>
  );
}

function MessageRow({
  caseId,
  m,
  onChange,
}: {
  caseId: string;
  m: CaseMessage;
  onChange: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(m.body);
  const [busy, setBusy] = useState(false);
  const isDraft = m.status === "draft" || m.status === "edited";

  async function save() {
    setBusy(true);
    try {
      await apiSend(`/api/cases/${caseId}/messages/${m.id}`, "PATCH", { subject: m.subject, body });
      setEditing(false);
      onChange();
    } finally {
      setBusy(false);
    }
  }
  async function approve() {
    setBusy(true);
    try {
      await apiSend(`/api/cases/${caseId}/messages/${m.id}/approve`, "POST");
      onChange();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="px-5 py-3.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-ink-subtle" />
          <span className="text-[13px] font-medium text-ink">{m.tone_label}</span>
          <Pill
            tone={m.status === "sent" ? "success" : m.status === "edited" ? "info" : "neutral"}
            className="px-1.5 py-0"
          >
            {m.status}
          </Pill>
        </div>
        <span className="text-xs text-ink-subtle">step {m.step_number}</span>
      </div>
      {m.subject && (
        <div className="mt-2 text-[13px] font-medium text-ink">{m.subject}</div>
      )}
      {editing ? (
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          className="mt-2 w-full rounded-md border border-border bg-surface p-2.5 text-[13px] leading-relaxed text-ink outline-none focus:border-accent"
        />
      ) : (
        <p className="mt-1.5 whitespace-pre-line text-[13px] leading-relaxed text-ink-muted">
          {m.body}
        </p>
      )}
      <div className="mt-2.5 flex items-center gap-2">
        {isDraft && !editing && (
          <>
            <button
              disabled={busy}
              onClick={approve}
              className="rounded-md bg-accent px-2.5 py-1 text-xs font-medium text-ink-invert transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              Approve & send
            </button>
            <button
              onClick={() => setEditing(true)}
              className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-ink transition-colors hover:bg-surface-hover"
            >
              Edit
            </button>
          </>
        )}
        {editing && (
          <>
            <button
              disabled={busy}
              onClick={save}
              className="rounded-md bg-accent px-2.5 py-1 text-xs font-medium text-ink-invert transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              Save draft
            </button>
            <button
              onClick={() => {
                setBody(m.body);
                setEditing(false);
              }}
              className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-ink-muted transition-colors hover:bg-surface-hover"
            >
              Cancel
            </button>
          </>
        )}
        {m.model && !editing && (
          <span className="ml-auto text-xs text-ink-subtle">{m.model}</span>
        )}
      </div>
    </div>
  );
}

function CaseSkeleton() {
  return (
    <div className="p-6">
      <Skeleton className="mb-4 h-4 w-28" />
      <Card className="mb-5 p-5">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="mt-2 h-3 w-64" />
      </Card>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-3 pb-5">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="flex-1">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="mt-2 h-10 w-full" />
              </div>
            </div>
          ))}
        </Card>
        <Card className="p-5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="mt-4 h-40 w-full" />
        </Card>
      </div>
    </div>
  );
}
