"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CheckCircle2, TrendingUp, BarChart2 } from "lucide-react";
import { CompletionTrendPoint } from "./types";

interface CompletionRateChartProps {
  data: CompletionTrendPoint[];
  averageRate?: number;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const p = payload[0].payload as CompletionTrendPoint;
    return (
      <div className="rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] p-3 shadow-lg space-y-1 text-xs">
        <p className="font-medium text-[var(--text-primary)]">
          {p.day}, {p.date}
        </p>
        <div className="flex items-center gap-2 text-[var(--accent)] font-medium">
          <span>Completion rate:</span>
          <span className="font-semibold">{p.rate}%</span>
        </div>
        <div className="text-[11px] text-[var(--text-secondary)] flex items-center gap-2 pt-1 border-t border-[var(--border-subtle)]">
          <span className="text-[#34c759]">{p.completed} completed</span>
          <span>•</span>
          <span className="text-rose-500">{p.missed} missed</span>
        </div>
      </div>
    );
  }
  return null;
};

export function CompletionRateChart({
  data,
  averageRate = 82,
}: CompletionRateChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="apple-card p-8 flex flex-col items-center justify-center min-h-[320px] text-center space-y-2">
        <BarChart2 className="w-8 h-8 text-[var(--text-secondary)] opacity-60" />
        <h4 className="text-base font-medium text-[var(--text-primary)]">No completion data yet</h4>
        <p className="text-xs text-[var(--text-secondary)] max-w-xs">
          Complete tasks on your daily schedule to visualize your adherence over time.
        </p>
      </div>
    );
  }

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Completion rate over time
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] font-medium">
              Avg {averageRate}%
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Daily execution ratio of completed vs scheduled blocks
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-[#34c759] font-medium">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>+6.4%</span>
        </div>
      </div>

      {/* Recharts Area Chart: Thin lines, no chart borders, muted gridlines */}
      <div className="h-64 w-full border-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="completionGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0071e3" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#0071e3" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(128,128,128,0.18)"
              vertical={false}
            />

            <XAxis
              dataKey="day"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />

            <YAxis
              domain={[0, 100]}
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="rate"
              stroke="#0071e3"
              strokeWidth={1.5}
              fillOpacity={1}
              fill="url(#completionGrad)"
              activeDot={{ r: 5, stroke: "#0071e3", strokeWidth: 2, fill: "var(--bg-elevated)" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
