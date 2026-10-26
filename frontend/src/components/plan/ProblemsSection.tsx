"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  AlertOctagon,
  Info,
  ArrowRight,
  CheckCircle,
  Wrench,
  Clock,
  Layers,
  Calendar,
  Minimize2,
  Trash2,
  PlusCircle,
  Loader2,
} from "lucide-react";
import { WorkloadProblem, RemedyOption } from "./types";

interface ProblemsSectionProps {
  problems: WorkloadProblem[];
  onApplyRemedy: (remedy: RemedyOption) => Promise<void>;
}

export function ProblemsSection({
  problems,
  onApplyRemedy,
}: ProblemsSectionProps) {
  const [applyingKey, setApplyingKey] = useState<string | null>(null);

  if (!problems || problems.length === 0) {
    return null;
  }

  const handleApply = async (problemId: string, remedy: RemedyOption, index: number) => {
    const key = `${problemId}-${remedy.action}-${index}`;
    setApplyingKey(key);
    try {
      await onApplyRemedy(remedy);
    } finally {
      setApplyingKey(null);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return {
          label: "Critical Bottleneck",
          color: "bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]",
          icon: AlertOctagon,
          cardBorder: "border-rose-500/30",
        };
      case "warning":
        return {
          label: "Capacity Warning",
          color: "bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)]",
          icon: AlertTriangle,
          cardBorder: "border-amber-500/30",
        };
      default:
        return {
          label: "Optimization",
          color: "bg-[var(--cat-blue-bg)] text-[var(--cat-blue-text)]",
          icon: Info,
          cardBorder: "border-[var(--border-hairline)]",
        };
    }
  };

  const getRemedyIcon = (action: string) => {
    switch (action) {
      case "split_task":
        return Minimize2;
      case "defer_task":
      case "move_forward":
        return Calendar;
      case "drop_task":
        return Trash2;
      case "expand_working_hours":
        return PlusCircle;
      default:
        return Wrench;
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)]">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
            Bottlenecks requiring remedy ({problems.length})
          </h3>
        </div>
        <span className="text-[11px] text-[var(--text-secondary)]">
          Real-time deterministic solver remedies
        </span>
      </div>

      {/* Problems Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {problems.map((problem) => {
          const badge = getSeverityBadge(problem.severity);
          const SeverityIcon = badge.icon;

          return (
            <div
              key={problem.id}
              className={`apple-card p-5 space-y-4 flex flex-col justify-between border ${badge.cardBorder}`}
            >
              <div className="space-y-3">
                {/* Card Top: Severity Badge and Type */}
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full border border-transparent flex items-center gap-1.5 ${badge.color}`}
                  >
                    <SeverityIcon className="w-3 h-3" />
                    {badge.label}
                  </span>
                  <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)] tracking-wider">
                    {problem.problem_type.replace(/_/g, " ")}
                  </span>
                </div>

                {/* Problem Description */}
                <div>
                  <p className="text-xs font-medium text-[var(--text-primary)] leading-relaxed">
                    {problem.description}
                  </p>
                </div>

                {/* Hours needed vs available */}
                {(problem.hours_needed !== null && problem.hours_needed !== undefined) ||
                (problem.hours_available !== null && problem.hours_available !== undefined) ? (
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    {problem.hours_needed !== null && (
                      <span className="px-2 py-0.5 rounded-full bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]">
                        Effort: {problem.hours_needed?.toFixed(1)}h
                      </span>
                    )}
                    {problem.hours_available !== null && (
                      <span className="px-2 py-0.5 rounded-full bg-[var(--fill-tertiary)] text-[var(--text-secondary)]">
                        Free window: {problem.hours_available?.toFixed(1)}h
                      </span>
                    )}
                  </div>
                ) : null}
              </div>

              {/* Remedies Section */}
              <div className="space-y-2 pt-2 border-t border-[var(--border-hairline)]">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Recommended Remedies:
                </span>

                <div className="space-y-2">
                  {problem.remedies.map((remedy, idx) => {
                    const RemedyIcon = getRemedyIcon(remedy.action);
                    const btnKey = `${problem.id}-${remedy.action}-${idx}`;
                    const isApplying = applyingKey === btnKey;

                    return (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-hairline)] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
                      >
                        <div className="space-y-0.5 flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <RemedyIcon className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
                            <h4 className="text-xs font-semibold text-[var(--text-primary)] truncate">
                              {remedy.title}
                            </h4>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                            {remedy.description}
                          </p>
                          <div className="pt-0.5">
                            <span className="text-[10px] font-mono font-medium text-emerald-500">
                              {remedy.impact_description || `+${remedy.impact_hours}h relief`}
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={() => handleApply(problem.id, remedy, idx)}
                          disabled={isApplying || applyingKey !== null}
                          aria-label={`Apply remedy: ${remedy.title}`}
                          className="self-end sm:self-center shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-medium text-[11px] shadow-sm transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        >
                          {isApplying ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin text-white" />
                              <span>Applying...</span>
                            </>
                          ) : (
                            <>
                              <span>Apply</span>
                              <ArrowRight className="w-3 h-3" />
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
