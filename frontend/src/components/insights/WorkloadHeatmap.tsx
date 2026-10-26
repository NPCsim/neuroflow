"use client";

import React from "react";
import { Calendar } from "lucide-react";
import { HeatmapDay } from "./types";

interface WorkloadHeatmapProps {
  days: HeatmapDay[];
  title?: string;
  description?: string;
}

export function WorkloadHeatmap({
  days,
  title = "Workload & capacity heatmap",
  description = "Daily workload intensity and cognitive overload risk",
}: WorkloadHeatmapProps) {
  if (!days || days.length === 0) {
    return (
      <div className="apple-card p-8 flex flex-col items-center justify-center min-h-[240px] text-center space-y-2">
        <Calendar className="w-8 h-8 text-[var(--text-secondary)] opacity-60" />
        <h4 className="text-base font-medium text-[var(--text-primary)]">No heatmap data available</h4>
        <p className="text-xs text-[var(--text-secondary)] max-w-xs">
          Schedule tasks in your weekly timeline to analyze daily capacity and cognitive load.
        </p>
      </div>
    );
  }

  // Soft desaturated pastel styling adhering strictly to DESIGN.md
  const getLoadStyling = (loadPct: number, isOverloaded: boolean) => {
    if (isOverloaded || loadPct > 100) {
      return {
        bg: "pastel-pink",
        badge: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
        label: "Overloaded",
      };
    }
    if (loadPct >= 80) {
      return {
        bg: "pastel-orange",
        badge: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
        label: "Heavy",
      };
    }
    if (loadPct >= 50) {
      return {
        bg: "pastel-green",
        badge: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
        label: "Optimal",
      };
    }
    if (loadPct > 0) {
      return {
        bg: "pastel-blue",
        badge: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
        label: "Light",
      };
    }
    return {
      bg: "pastel-gray",
      badge: "bg-[var(--bg-secondary)] text-[var(--text-secondary)]",
      label: "Open",
    };
  };

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              {title}
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-medium">
              {days.length} days horizon
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">{description}</p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full pastel-blue" />
            <span>&lt;50%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full pastel-green" />
            <span>50–80%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full pastel-orange" />
            <span>80–100%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full pastel-pink" />
            <span>&gt;100%</span>
          </div>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
        {days.map((d, idx) => {
          const style = getLoadStyling(d.loadPct, d.isOverloaded);
          const formattedDate = d.date.includes("-")
            ? d.date.split("-").slice(1).join("/")
            : d.date;

          return (
            <div
              key={idx}
              className={`relative rounded-xl p-3 border transition-all duration-200 cursor-default ${style.bg} ${
                d.isToday ? "ring-2 ring-[var(--accent)] ring-offset-2 ring-offset-[var(--bg-elevated)]" : ""
              }`}
            >
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-semibold">{d.dayOfWeek}</span>
                <span className="text-[11px] opacity-75">{formattedDate}</span>
              </div>
              <div className="text-lg font-light tracking-tight mt-1">
                {d.loadPct}%
              </div>
              <div className="text-[11px] opacity-75 mt-0.5">
                {d.scheduledHours.toFixed(1)} / {d.capacityHours.toFixed(0)}h
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
