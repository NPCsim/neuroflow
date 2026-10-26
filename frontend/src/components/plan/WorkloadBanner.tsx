"use client";

import React from "react";
import {
  Sparkles,
  RefreshCw,
  Activity,
  Gauge,
  Clock,
  CalendarCheck,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { WorkloadAnalysis, DayLoad } from "./types";

interface WorkloadBannerProps {
  workload?: WorkloadAnalysis | null;
  todayLoad?: DayLoad | null;
  onReplan: () => void;
  replanning: boolean;
}

export function WorkloadBanner({
  workload,
  todayLoad,
  onReplan,
  replanning,
}: WorkloadBannerProps) {
  const realismScore = workload?.realism_score ?? 75;

  // Calculate today load %
  const todayPercentage = todayLoad
    ? Math.round(todayLoad.load_percentage)
    : workload?.daily_loads?.[0]
    ? Math.round(workload.daily_loads[0].load_percentage)
    : 65;

  const scheduledMinutes = todayLoad?.scheduled_minutes ?? 180;
  const capacityMinutes = todayLoad?.capacity_minutes ?? 480;
  const fixedMinutes = todayLoad?.fixed_event_minutes ?? 30;
  const scheduledHours = (scheduledMinutes / 60).toFixed(1);
  const fixedHours = (fixedMinutes / 60).toFixed(1);
  const capacityHours = (capacityMinutes / 60).toFixed(1);

  // Status badges
  const getScoreBadge = (score: number) => {
    if (score >= 80) {
      return {
        label: "Optimal Realism",
        color: "bg-[var(--cat-green-bg)] text-[var(--cat-green-text)]",
        icon: CheckCircle2,
        barColor: "bg-emerald-500",
      };
    } else if (score >= 60) {
      return {
        label: "Tight Feasibility",
        color: "bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)]",
        icon: AlertTriangle,
        barColor: "bg-amber-500",
      };
    } else {
      return {
        label: "Overloaded",
        color: "bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]",
        icon: AlertOctagon,
        barColor: "bg-rose-500",
      };
    }
  };

  const getLoadBadge = (pct: number) => {
    if (pct > 100) {
      return {
        label: "Overloaded",
        color: "bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]",
        icon: AlertOctagon,
      };
    } else if (pct >= 85) {
      return {
        label: "High Load",
        color: "bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)]",
        icon: AlertTriangle,
      };
    } else {
      return {
        label: "Healthy Load",
        color: "bg-[var(--cat-green-bg)] text-[var(--cat-green-text)]",
        icon: CheckCircle2,
      };
    }
  };

  const scoreBadge = getScoreBadge(realismScore);
  const loadBadge = getLoadBadge(todayPercentage);
  const ScoreIcon = scoreBadge.icon;
  const LoadIcon = loadBadge.icon;

  return (
    <div className="apple-card p-6 transition-all duration-200">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        {/* Left Section: Workload Metrics */}
        <div className="flex-1 space-y-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[var(--accent)]/10 text-[var(--accent)]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                  Workload & Feasibility Pulse
                </h2>
                <span className="text-[11px] font-normal text-[var(--text-secondary)]">
                  {todayLoad?.day_of_week || "Today"}, {todayLoad?.date || "Active Horizon"}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Deterministic capacity solver enforcing working hours and non-overlap guarantees
              </p>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-1">
            {/* Metric 1: Today's Load % */}
            <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[var(--accent)]" />
                  Today&apos;s load
                </span>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border border-transparent flex items-center gap-1 ${loadBadge.color}`}
                >
                  <LoadIcon className="w-3 h-3" />
                  {loadBadge.label}
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-semibold text-[var(--text-primary)] tracking-tight font-mono">
                  {todayPercentage}%
                </span>
                <span className="text-[11px] text-[var(--text-secondary)]">
                  of {capacityHours}h capacity
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-[var(--fill-tertiary)] rounded-full h-1.5 overflow-hidden flex">
                <div
                  className={`h-full transition-all duration-500 ${
                    todayPercentage > 100
                      ? "bg-rose-500"
                      : todayPercentage > 85
                      ? "bg-amber-500"
                      : "bg-[var(--accent)]"
                  }`}
                  style={{ width: `${Math.min(todayPercentage, 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-[10px] text-[var(--text-secondary)] font-mono">
                <span>Focus: {scheduledHours}h</span>
                <span>Fixed: {fixedHours}h</span>
                <span>Limit: {capacityHours}h</span>
              </div>
            </div>

            {/* Metric 2: Realism Score */}
            <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5 text-indigo-400" />
                  Realism score
                </span>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border border-transparent flex items-center gap-1 ${scoreBadge.color}`}
                >
                  <ScoreIcon className="w-3 h-3" />
                  {scoreBadge.label}
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-semibold text-[var(--text-primary)] tracking-tight font-mono">
                  {realismScore}
                </span>
                <span className="text-xs text-[var(--text-secondary)] font-normal">/ 100</span>
              </div>

              {/* Realism meter */}
              <div className="w-full bg-[var(--fill-tertiary)] rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${scoreBadge.barColor}`}
                  style={{ width: `${Math.max(5, Math.min(realismScore, 100))}%` }}
                />
              </div>

              <p className="text-[10px] text-[var(--text-secondary)]">
                {workload?.problems?.length
                  ? `${workload.problems.length} bottleneck(s) require remedy`
                  : "Zero deadline deficits detected across horizon"}
              </p>
            </div>

            {/* Metric 3: Horizon Capacity Summary */}
            <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-2 sm:col-span-2 md:col-span-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                  <CalendarCheck className="w-3.5 h-3.5 text-emerald-500" />
                  Horizon summary
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--fill-tertiary)] text-[var(--text-secondary)]">
                  7-Day Scope
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-semibold text-[var(--text-primary)] tracking-tight font-mono">
                  {workload?.total_scheduled_hours?.toFixed(1) ?? "0.0"}h
                </span>
                <span className="text-[11px] text-[var(--text-secondary)]">planned work</span>
              </div>

              <div className="text-[10px] text-[var(--text-secondary)] space-y-0.5 font-mono">
                <div className="flex justify-between">
                  <span>Available:</span>
                  <span className="text-[var(--text-primary)] font-medium">
                    {workload?.total_capacity_hours?.toFixed(1) ?? "40.0"}h
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Fixed:</span>
                  <span className="text-[var(--text-primary)] font-medium">
                    {workload?.total_fixed_event_hours?.toFixed(1) ?? "0.0"}h
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section: Replan Now Action CTA */}
        <div className="lg:w-60 flex flex-col justify-center items-start lg:items-end p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-3 shrink-0">
          <div className="space-y-0.5 text-left lg:text-right">
            <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center lg:justify-end gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
              Schedule Maintenance
            </span>
            <p className="text-[11px] text-[var(--text-secondary)]">
              Sweep past unfinished blocks into future openings.
            </p>
          </div>

          <button
            onClick={onReplan}
            disabled={replanning}
            aria-label="Replan now"
            className="w-full lg:w-auto px-5 py-2.5 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] active:scale-95 text-white font-medium text-xs shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${replanning ? "animate-spin" : ""}`} />
            <span>{replanning ? "Re-optimizing..." : "Replan now"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
