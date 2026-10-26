"use client";

import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Layers } from "lucide-react";
import { CategoryFocusPoint } from "./types";

interface FocusCategoryPieChartProps {
  data: CategoryFocusPoint[];
  totalHours?: number;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const p = payload[0].payload as CategoryFocusPoint;
    return (
      <div className="rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] p-3 shadow-lg space-y-1 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="font-semibold text-[var(--text-primary)] capitalize">{p.name}</span>
        </div>
        <div className="text-[var(--text-secondary)] text-[11px]">
          {p.hours.toFixed(1)} hours ({p.percentage}%)
        </div>
      </div>
    );
  }
  return null;
};

export function FocusCategoryPieChart({
  data,
  totalHours = 24.5,
}: FocusCategoryPieChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="apple-card p-8 flex flex-col items-center justify-center min-h-[320px] text-center space-y-2">
        <Layers className="w-8 h-8 text-[var(--text-secondary)] opacity-60" />
        <h4 className="text-base font-medium text-[var(--text-primary)]">No category distribution</h4>
        <p className="text-xs text-[var(--text-secondary)] max-w-xs">
          Categorized tasks and goal focus blocks will generate your time allocation breakdown here.
        </p>
      </div>
    );
  }

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
            Focus time by category
          </h3>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-medium">
            {totalHours.toFixed(1)}h total
          </span>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Proportional allocation of deep work across objectives
        </p>
      </div>

      {/* Donut Chart & Category Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-center">
        {/* Recharts Pie Chart */}
        <div className="h-56 relative flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={58}
                outerRadius={86}
                paddingAngle={4}
                dataKey="hours"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    stroke="var(--bg-elevated)"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center Callout inside Donut */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-3xl font-light text-[var(--text-primary)] tracking-tight">
              {totalHours.toFixed(1)}h
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] font-medium">
              Deep focus
            </span>
          </div>
        </div>

        {/* Legend List */}
        <div className="space-y-2">
          {data.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-[var(--bg-secondary)] text-xs"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="font-medium text-[var(--text-primary)] capitalize truncate">{item.name}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-[var(--text-secondary)]">{item.hours.toFixed(1)}h</span>
                <span className="font-semibold text-[var(--text-primary)] w-9 text-right">{item.percentage}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
