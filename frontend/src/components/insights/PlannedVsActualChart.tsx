"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Clock } from "lucide-react";
import { PlannedVsActualPoint } from "./types";

interface PlannedVsActualChartProps {
  data: PlannedVsActualPoint[];
  overallRatio?: number;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const p = payload[0].payload as PlannedVsActualPoint;
    const diff = p.actualHours - p.plannedHours;
    return (
      <div className="rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] p-3 shadow-lg space-y-1 text-xs">
        <p className="font-semibold text-[var(--text-primary)]">{p.category}</p>
        <div className="flex justify-between gap-4 text-[var(--text-secondary)]">
          <span>Planned:</span>
          <span className="font-medium text-[var(--text-primary)]">{p.plannedHours.toFixed(1)}h</span>
        </div>
        <div className="flex justify-between gap-4 text-[var(--accent)]">
          <span>Actual:</span>
          <span className="font-medium">{p.actualHours.toFixed(1)}h</span>
        </div>
        <div className="pt-1 border-t border-[var(--border-subtle)] flex justify-between gap-4 text-[11px]">
          <span className="text-[var(--text-secondary)]">Variance:</span>
          <span
            className={`font-semibold ${
              diff > 0 ? "text-[#ff9500]" : diff < 0 ? "text-[#34c759]" : "text-[var(--text-secondary)]"
            }`}
          >
            {diff > 0 ? `+${diff.toFixed(1)}h buffer` : `${diff.toFixed(1)}h savings`}
          </span>
        </div>
      </div>
    );
  }
  return null;
};

export function PlannedVsActualChart({
  data,
  overallRatio = 1.08,
}: PlannedVsActualChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="apple-card p-8 flex flex-col items-center justify-center min-h-[320px] text-center space-y-2">
        <Clock className="w-8 h-8 text-[var(--text-secondary)] opacity-60" />
        <h4 className="text-base font-medium text-[var(--text-primary)]">No duration tracking yet</h4>
        <p className="text-xs text-[var(--text-secondary)] max-w-xs">
          Planned and actual task durations will be compared here as you log and complete tasks.
        </p>
      </div>
    );
  }

  const isOverrun = overallRatio > 1.05;

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Planned vs actual hours
            </h3>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                isOverrun
                  ? "bg-[#ff9500]/10 text-[#c96500] dark:text-[#ff9f0a]"
                  : "bg-[#34c759]/10 text-[#248a3d] dark:text-[#30d158]"
              }`}
            >
              {overallRatio}x ratio
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Estimation accuracy by task category (planned vs spent)
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--text-secondary)] opacity-40" /> Planned
          </span>
          <span className="flex items-center gap-1.5 text-[var(--accent)] font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent)]" /> Actual
          </span>
        </div>
      </div>

      {/* Recharts Bar Chart: Rounded bars, no chart borders, muted gridlines */}
      <div className="h-64 w-full border-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(128,128,128,0.18)"
              vertical={false}
            />

            <XAxis
              dataKey="category"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />

            <YAxis
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}h`}
            />

            <Tooltip content={<CustomTooltip />} />

            <Bar
              dataKey="plannedHours"
              name="Planned"
              fill="rgba(120, 120, 128, 0.2)"
              radius={[6, 6, 0, 0]}
              maxBarSize={28}
            />
            <Bar
              dataKey="actualHours"
              name="Actual"
              fill="#0071e3"
              radius={[6, 6, 0, 0]}
              maxBarSize={28}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
