"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ReasonStat, TimePoint } from "@/lib/types";

const ACCENT = "#635bff";
const SUCCESS = "#1a7f53";
const NEUTRAL = "#c3c9d2";
const AXIS = "#8a93a3";
const GRID = "#eceef1";

const REASON_COLORS = [
  "#635bff", "#1f6fb2", "#1a7f53", "#9a6700",
  "#b42318", "#7c5cff", "#0f8a8a", "#5b6472",
];

function weekLabel(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function usd(minor: number, compact = false) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 0,
  }).format(minor / 100);
}

function TooltipBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-[var(--shadow-pop)]">
      {children}
    </div>
  );
}

export function RecoveredRevenueChart({ data }: { data: TimePoint[] }) {
  return (
    <div className="h-[220px] w-full px-2 pb-2 pt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ACCENT} stopOpacity={0.18} />
              <stop offset="100%" stopColor={ACCENT} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="week"
            tickFormatter={weekLabel}
            tick={{ fontSize: 11, fill: AXIS }}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            minTickGap={24}
          />
          <YAxis
            tickFormatter={(v) => usd(v, true)}
            tick={{ fontSize: 11, fill: AXIS }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip
            cursor={{ stroke: ACCENT, strokeOpacity: 0.3 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox>
                  <div className="font-medium text-ink">
                    {weekLabel(payload[0].payload.week)}
                  </div>
                  <div className="mt-0.5 text-ink-muted">
                    Recovered{" "}
                    <span className="font-semibold text-ink tnum">
                      {usd(payload[0].payload.recovered_usd_minor)}
                    </span>
                  </div>
                </TooltipBox>
              ) : null
            }
          />
          <Area
            type="monotone"
            dataKey="recovered_usd_minor"
            stroke={ACCENT}
            strokeWidth={2}
            fill="url(#rev)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RecoveryCadenceChart({ data }: { data: TimePoint[] }) {
  return (
    <div className="h-[220px] w-full px-2 pb-2 pt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 12, left: 4, bottom: 0 }} barGap={2}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="week"
            tickFormatter={weekLabel}
            tick={{ fontSize: 11, fill: AXIS }}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            minTickGap={24}
          />
          <YAxis
            tick={{ fontSize: 11, fill: AXIS }}
            tickLine={false}
            axisLine={false}
            width={28}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: "#f0f1f4" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox>
                  <div className="font-medium text-ink">
                    {weekLabel(payload[0].payload.week)}
                  </div>
                  <div className="mt-0.5 text-ink-muted">
                    {payload[0].payload.opened} opened ·{" "}
                    <span className="text-success">{payload[0].payload.recovered} recovered</span>
                  </div>
                </TooltipBox>
              ) : null
            }
          />
          <Bar dataKey="opened" fill={NEUTRAL} radius={[2, 2, 0, 0]} />
          <Bar dataKey="recovered" fill={SUCCESS} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ReasonBars({ data }: { data: ReasonStat[] }) {
  const rows = data.slice(0, 8);
  return (
    <div className="h-[260px] w-full px-2 pb-2 pt-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 0, right: 16, left: 4, bottom: 0 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 11, fill: "#5b6472" }}
            tickLine={false}
            axisLine={false}
            width={132}
          />
          <Tooltip
            cursor={{ fill: "#f0f1f4" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox>
                  <div className="font-medium text-ink">{payload[0].payload.label}</div>
                  <div className="mt-0.5 text-ink-muted">
                    {payload[0].payload.count} cases ·{" "}
                    {usd(payload[0].payload.at_risk_usd_minor)} at risk ·{" "}
                    {(payload[0].payload.recovery_rate * 100).toFixed(0)}% recovered
                  </div>
                </TooltipBox>
              ) : null
            }
          />
          <Bar dataKey="count" radius={[0, 3, 3, 0]} barSize={16}>
            {rows.map((_, i) => (
              <Cell key={i} fill={REASON_COLORS[i % REASON_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
