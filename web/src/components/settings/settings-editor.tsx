"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { ArrowUpRight, Check, Mail, Sparkles } from "lucide-react";
import { apiSend, swrFetcher } from "@/lib/api";
import { cn } from "@/lib/utils";
import { FAILURE_CODES, Policy, PolicyPreview, TONES } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";

interface Draft {
  max_retries: number;
  backoff_days: number[];
  retry_window_days: number;
  escalate_after_step: number;
  base_tone: string;
  brand_voice: string;
  auto_send: boolean;
}

function fromPolicy(p: Policy): Draft {
  return {
    max_retries: p.max_retries,
    backoff_days: p.backoff_days,
    retry_window_days: p.retry_window_days,
    escalate_after_step: p.escalate_after_step,
    base_tone: p.base_tone,
    brand_voice: p.brand_voice,
    auto_send: p.auto_send,
  };
}

export function SettingsEditor() {
  const { data: policy, error, mutate } = useSWR<Policy>("/api/policy", swrFetcher);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [code, setCode] = useState("insufficient_funds");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (policy && !draft) setDraft(fromPolicy(policy));
  }, [policy, draft]);

  const dirty = useMemo(
    () => !!policy && !!draft && JSON.stringify(draft) !== JSON.stringify(fromPolicy(policy)),
    [policy, draft],
  );

  if (error) return <div className="p-6"><ErrorState /></div>;
  if (!draft) return <SettingsSkeleton />;

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setSaved(false);
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  }

  function setRetries(n: number) {
    const next = Math.max(0, Math.min(8, n));
    setDraft((d) => {
      if (!d) return d;
      const b = [...d.backoff_days];
      while (b.length < next) b.push((b[b.length - 1] ?? 2) + 2);
      b.length = next;
      return { ...d, max_retries: next, backoff_days: b };
    });
    setSaved(false);
  }

  async function save() {
    setSaving(true);
    try {
      await apiSend("/api/policy", "PATCH", draft);
      await mutate();
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* ── Editor ── */}
      <div className="space-y-5">
        <Card>
          <CardHeader title="Retry policy" subtitle="How hard the agent tries before a human steps in." />
          <div className="space-y-5 p-5">
            <Field label="Max automated retries" hint="Hard declines (stolen card, fraud) ignore this.">
              <Stepper value={draft.max_retries} onChange={setRetries} min={0} max={8} />
            </Field>

            <Field label="Backoff between retries (days)" hint="Insufficient-funds retries straddle payday.">
              <div className="flex flex-wrap gap-2">
                {draft.backoff_days.length === 0 && (
                  <span className="text-[13px] text-ink-subtle">No retries scheduled.</span>
                )}
                {draft.backoff_days.map((d, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <span className="text-xs text-ink-subtle">#{i + 1}</span>
                    <input
                      type="number"
                      min={0}
                      max={60}
                      value={d}
                      onChange={(e) => {
                        const v = Math.max(0, Math.min(60, Number(e.target.value)));
                        const b = [...draft.backoff_days];
                        b[i] = v;
                        set("backoff_days", b);
                      }}
                      className="w-14 rounded-md border border-border bg-surface px-2 py-1 text-center text-[13px] text-ink tnum outline-none focus:border-accent"
                    />
                  </div>
                ))}
              </div>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Recovery window (days)">
                <Stepper
                  value={draft.retry_window_days}
                  onChange={(v) => set("retry_window_days", Math.max(1, Math.min(90, v)))}
                />
              </Field>
              <Field label="Escalate after step">
                <Stepper
                  value={draft.escalate_after_step}
                  onChange={(v) => set("escalate_after_step", Math.max(1, Math.min(8, v)))}
                />
              </Field>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Message tone" subtitle="The voice the agent writes in." />
          <div className="space-y-5 p-5">
            <Field label="Starting tone" hint="Where the escalation ladder begins.">
              <div className="flex flex-wrap gap-1.5">
                {TONES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => set("base_tone", t.value)}
                    className={cn(
                      "rounded-md border px-2.5 py-1 text-[13px] font-medium transition-colors",
                      draft.base_tone === t.value
                        ? "border-accent bg-accent-soft text-accent-ink"
                        : "border-border text-ink-muted hover:bg-surface-hover",
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Brand voice" hint="Guides the live agent's wording.">
              <textarea
                value={draft.brand_voice}
                onChange={(e) => set("brand_voice", e.target.value)}
                rows={3}
                className="w-full rounded-md border border-border bg-surface p-2.5 text-[13px] leading-relaxed text-ink outline-none focus:border-accent"
              />
            </Field>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-[13px] font-medium text-ink">Auto-send messages</div>
                <div className="text-xs text-ink-subtle">
                  Off keeps a human in the loop — drafts wait for approval.
                </div>
              </div>
              <Toggle checked={draft.auto_send} onChange={(v) => set("auto_send", v)} />
            </div>
          </div>
        </Card>

        <div className="flex items-center gap-3">
          <button
            disabled={!dirty || saving}
            onClick={save}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-ink-invert transition-colors hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save policy"}
          </button>
          {saved && !dirty && (
            <span className="inline-flex items-center gap-1.5 text-[13px] text-success">
              <Check className="h-3.5 w-3.5" /> Saved — new cases use this policy
            </span>
          )}
          {dirty && (
            <button
              onClick={() => policy && setDraft(fromPolicy(policy))}
              className="text-[13px] text-ink-muted hover:text-ink"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* ── Live preview ── */}
      <div className="lg:sticky lg:top-20 lg:self-start">
        <PreviewPane draft={draft} code={code} setCode={setCode} />
      </div>
    </div>
  );
}

function PreviewPane({
  draft,
  code,
  setCode,
}: {
  draft: Draft;
  code: string;
  setCode: (c: string) => void;
}) {
  const body = useMemo(
    () => ({
      failure_code: code,
      max_retries: draft.max_retries,
      backoff_days: draft.backoff_days,
      base_tone: draft.base_tone,
      brand_voice: draft.brand_voice,
      auto_send: draft.auto_send,
    }),
    [code, draft],
  );
  const [preview, setPreview] = useState<PolicyPreview | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const id = setTimeout(async () => {
      try {
        const p = await apiSend<PolicyPreview>("/api/policy/preview", "POST", body);
        if (alive) setPreview(p);
      } finally {
        if (alive) setLoading(false);
      }
    }, 250);
    return () => {
      alive = false;
      clearTimeout(id);
    };
  }, [body]);

  return (
    <Card>
      <CardHeader
        title="Agent preview"
        subtitle="A sample failure, run through the policy above — live."
        action={
          <select
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-ink-muted outline-none focus:border-accent"
          >
            {FAILURE_CODES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        }
      />
      {!preview ? (
        <div className="space-y-3 p-5">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <div className={cn("p-5 transition-opacity", loading && "opacity-60")}>
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="accent">{preview.failure_label}</Pill>
            {preview.decided_by === "claude" && (
              <Pill tone="info" className="px-1.5 py-0">
                <Sparkles className="h-2.5 w-2.5" /> Claude
              </Pill>
            )}
            <span className="text-xs text-ink-subtle">
              {Math.round(preview.confidence * 100)}% confidence
            </span>
          </div>

          {/* Plan */}
          <div className="mt-3 rounded-md border border-border bg-surface-subtle p-3">
            <div className="flex flex-wrap items-center gap-2 text-[13px]">
              {preview.max_attempts === 0 ? (
                <span className="inline-flex items-center gap-1.5 font-medium text-warning">
                  <ArrowUpRight className="h-3.5 w-3.5" />
                  No retries — escalate to{" "}
                  {(preview.escalation_target ?? "a human").replace("_", " ")}
                </span>
              ) : (
                <>
                  <span className="font-medium text-ink">
                    {preview.max_attempts} retr{preview.max_attempts === 1 ? "y" : "ies"}:
                  </span>
                  {preview.backoff_days.map((d, i) => (
                    <span
                      key={i}
                      className="rounded bg-accent-soft px-1.5 py-0.5 text-xs font-medium text-accent-ink tnum"
                    >
                      +{d}d
                    </span>
                  ))}
                  <span className="text-ink-subtle">
                    then → {(preview.escalation_target ?? "human").replace("_", " ")}
                  </span>
                </>
              )}
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-muted">
              {preview.strategy_reasoning}
            </p>
          </div>

          {/* Drafted message */}
          {preview.message ? (
            <div className="mt-4">
              <div className="mb-1.5 flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-ink-subtle" />
                <span className="text-[13px] font-medium text-ink">
                  {preview.message.tone_label}
                </span>
                <Pill tone={preview.auto_send ? "info" : "neutral"} className="px-1.5 py-0">
                  {preview.auto_send ? "auto-sent" : "held for approval"}
                </Pill>
              </div>
              <div className="rounded-md border border-border p-3">
                {preview.message.subject && (
                  <div className="text-[13px] font-medium text-ink">
                    {preview.message.subject}
                  </div>
                )}
                <p className="mt-1.5 whitespace-pre-line text-[13px] leading-relaxed text-ink-muted">
                  {preview.message.body}
                </p>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-[13px] text-ink-subtle">
              No customer message for this failure type — the agent routes it straight to a human.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[13px] font-medium text-ink">{label}</div>
      {hint && <div className="mb-2 mt-0.5 text-xs text-ink-subtle">{hint}</div>}
      <div className={hint ? "" : "mt-2"}>{children}</div>
    </div>
  );
}

function Stepper({
  value,
  onChange,
  min = 0,
  max = 90,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div className="inline-flex items-center rounded-md border border-border">
      <button
        onClick={() => onChange(Math.max(min, value - 1))}
        className="px-2.5 py-1 text-ink-muted transition-colors hover:bg-surface-hover"
      >
        −
      </button>
      <span className="w-10 text-center text-[13px] font-semibold text-ink tnum">{value}</span>
      <button
        onClick={() => onChange(Math.min(max, value + 1))}
        className="px-2.5 py-1 text-ink-muted transition-colors hover:bg-surface-hover"
      >
        +
      </button>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-5 w-9 shrink-0 rounded-full transition-colors",
        checked ? "bg-accent" : "bg-border-strong",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-4 w-4 rounded-full bg-surface shadow-sm transition-transform",
          checked ? "translate-x-4" : "translate-x-0.5",
        )}
      />
    </button>
  );
}

function SettingsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-2">
      {Array.from({ length: 2 }).map((_, i) => (
        <Card key={i} className="p-5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-4 h-32 w-full" />
        </Card>
      ))}
    </div>
  );
}
