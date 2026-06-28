// Types mirroring the FastAPI response models (app/schemas/api.py).

export interface DashboardSummary {
  reporting_currency: string;
  at_risk_usd_minor: number;
  recovered_usd_minor: number;
  written_off_usd_minor: number;
  recovery_rate: number;
  amount_recovery_rate: number;
  total_cases: number;
  open_cases: number;
  in_progress: number;
  escalated: number;
  recovered: number;
  written_off: number;
  paused: number;
  needs_human: number;
  avg_recovery_hours: number | null;
  customers: number;
}

export interface TimePoint {
  week: string;
  opened: number;
  recovered: number;
  recovered_usd_minor: number;
  at_risk_usd_minor: number;
}

export interface ReasonStat {
  code: string;
  label: string;
  count: number;
  at_risk_usd_minor: number;
  recovered_usd_minor: number;
  recovery_rate: number;
}

export type CaseStatus =
  | "in_progress"
  | "recovered"
  | "escalated"
  | "written_off"
  | "paused";

export interface QueueItem {
  id: string;
  customer_name: string;
  company: string | null;
  email: string;
  amount_minor: number;
  currency: string;
  amount_usd_minor: number;
  failure_code: string;
  failure_label: string;
  status: CaseStatus;
  current_step: number;
  total_steps: number;
  next_action_label: string | null;
  next_action_at: string | null;
  opened_at: string;
  resolved_at: string | null;
  confidence: number | null;
  requires_human: boolean;
  decided_by: string | null;
}

export interface QueuePage {
  items: QueueItem[];
  total: number;
  counts_by_status: Record<string, number>;
}

export interface CaseEvent {
  id: string;
  type: string;
  actor: "agent" | "human" | "system";
  title: string;
  reasoning: string | null;
  detail: Record<string, unknown> | null;
  step_number: number | null;
  message_id: string | null;
  payment_id: string | null;
  occurred_at: string;
}

export interface CaseMessage {
  id: string;
  channel: string;
  tone: string;
  tone_label: string;
  status: "draft" | "approved" | "sent" | "edited";
  step_number: number | null;
  subject: string | null;
  body: string;
  model: string | null;
  created_at: string;
  sent_at: string | null;
}

export interface CaseDetail extends QueueItem {
  plan_name: string | null;
  interval: string | null;
  plan: Record<string, unknown> | null;
  recovered_minor: number;
  escalated_to: string | null;
  summary: string | null;
  events: CaseEvent[];
  messages: CaseMessage[];
}

export const STATUS_META: Record<
  CaseStatus,
  { label: string; tone: "success" | "info" | "warning" | "danger" | "neutral" }
> = {
  recovered: { label: "Recovered", tone: "success" },
  in_progress: { label: "In progress", tone: "info" },
  escalated: { label: "Escalated", tone: "warning" },
  written_off: { label: "Written off", tone: "danger" },
  paused: { label: "Paused", tone: "neutral" },
};
