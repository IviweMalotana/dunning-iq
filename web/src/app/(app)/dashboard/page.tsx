import Link from "next/link";
import { apiGet } from "@/lib/api";
import { formatMoney, formatPercent } from "@/lib/utils";
import { DashboardSummary, ReasonStat, TimePoint } from "@/lib/types";
import { PageHeader } from "@/components/shell/page-header";
import { Card, CardHeader } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";
import { StatCard } from "@/components/dashboard/stat-card";
import {
  RecoveredRevenueChart,
  RecoveryCadenceChart,
  ReasonBars,
} from "@/components/dashboard/charts";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [summary, timeseries, reasons] = await Promise.all([
    apiGet<DashboardSummary>("/api/dashboard/summary"),
    apiGet<TimePoint[]>("/api/dashboard/timeseries"),
    apiGet<ReasonStat[]>("/api/dashboard/by-reason"),
  ]);

  const statusRows: { label: string; key: keyof DashboardSummary; tone: string }[] = [
    { label: "In progress", key: "in_progress", tone: "info" },
    { label: "Escalated", key: "escalated", tone: "warning" },
    { label: "Recovered", key: "recovered", tone: "success" },
    { label: "Written off", key: "written_off", tone: "danger" },
    { label: "Paused", key: "paused", tone: "neutral" },
  ];

  return (
    <>
      <PageHeader
        title="Recovery"
        subtitle="Live view of revenue at risk and what the agent is recovering."
      />
      <div className="space-y-5 p-6">
        {/* KPIs */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Recovered revenue"
            value={formatMoney(summary.recovered_usd_minor, "USD")}
            tone="success"
            sub={`${summary.recovered} of ${summary.total_cases} cases recovered`}
          />
          <StatCard
            label="At-risk revenue"
            value={formatMoney(summary.at_risk_usd_minor, "USD")}
            tone="warning"
            sub={`${summary.open_cases} open cases`}
          />
          <StatCard
            label="Recovery rate"
            value={formatPercent(summary.recovery_rate)}
            sub={`${formatPercent(summary.amount_recovery_rate)} of at-risk $ recovered`}
          />
          <StatCard
            label="Needs a human"
            value={String(summary.needs_human)}
            accent
            sub={
              summary.avg_recovery_hours != null
                ? `Avg recovery in ${summary.avg_recovery_hours}h`
                : "Escalations awaiting review"
            }
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="Recovered revenue" subtitle="Per week, last 12 weeks (USD)" />
            <RecoveredRevenueChart data={timeseries} />
          </Card>
          <Card>
            <CardHeader title="Recovery cadence" subtitle="Cases opened vs recovered each week" />
            <RecoveryCadenceChart data={timeseries} />
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader title="Failures by reason" subtitle="Where the at-risk revenue is" />
            <ReasonBars data={reasons} />
          </Card>
          <Card>
            <CardHeader
              title="Queue snapshot"
              action={
                <Link
                  href="/queue"
                  className="text-xs font-medium text-accent-ink hover:underline"
                >
                  Open queue →
                </Link>
              }
            />
            <div className="divide-y divide-border">
              {statusRows.map((r) => (
                <div key={r.label} className="flex items-center justify-between px-5 py-3">
                  <Pill tone={r.tone as never}>{r.label}</Pill>
                  <span className="text-sm font-semibold text-ink tnum">
                    {summary[r.key] as number}
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between px-5 py-3">
                <span className="text-[13px] text-ink-muted">Customers tracked</span>
                <span className="text-sm font-semibold text-ink tnum">
                  {summary.customers}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
