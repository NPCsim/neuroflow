"use client";

import React from "react";
import { Flame, Trophy } from "lucide-react";

interface StreakCounterProps {
  currentStreak?: number;
  bestStreak?: number;
  activeDays?: string[];
}

export function StreakCounter({
  currentStreak = 5,
  bestStreak = 12,
  activeDays = ["Mon", "Tue", "Wed", "Thu", "Fri"],
}: StreakCounterProps) {
  const weekDays = [
    { label: "M", name: "Mon" },
    { label: "T", name: "Tue" },
    { label: "W", name: "Wed" },
    { label: "T", name: "Thu" },
    { label: "F", name: "Fri" },
    { label: "S", name: "Sat" },
    { label: "S", name: "Sun" },
  ];

  const getStreakMessage = (streak: number) => {
    if (streak >= 10) return "Master of consistency. Unstoppable cognitive flow.";
    if (streak >= 5) return "Great rhythm. Focus blocks are clicking into place.";
    if (streak >= 1) return "Momentum building. Finish today's blocks strong.";
    return "Complete your first focus block today to kick off a new streak.";
  };

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#ff9500]/10 text-[#ff9500] flex items-center justify-center">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Focus execution streak
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">Consecutive days adhering to schedule</p>
          </div>
        </div>

        {/* Best Record Pill */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--bg-secondary)] text-xs text-[var(--text-secondary)]">
          <Trophy className="w-3.5 h-3.5 text-[#ff9500]" />
          <span>Best:</span>
          <span className="font-semibold text-[var(--text-primary)]">{bestStreak}d</span>
        </div>
      </div>

      {/* Main Metric Row: Big light-weight numeral */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 pt-1">
        <div className="flex items-baseline gap-3">
          <span className="text-5xl font-light text-[var(--text-primary)] tracking-tight">
            {currentStreak}
          </span>
          <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
            Day{currentStreak !== 1 ? "s" : ""} strong
          </span>
        </div>

        <span className="text-xs text-[var(--text-secondary)] max-w-sm">
          {getStreakMessage(currentStreak)}
        </span>
      </div>

      {/* Weekly Check-in Circles */}
      <div className="pt-4 border-t border-[var(--border-subtle)] flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-[var(--text-secondary)]">
          Past 7 days
        </span>
        <div className="flex items-center gap-2.5">
          {weekDays.map((d, idx) => {
            const isCompleted = activeDays.includes(d.name);
            const isToday = d.name === "Mon";

            return (
              <div key={idx} className="flex flex-col items-center gap-1">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
                    isCompleted
                      ? "bg-[#ff9500] text-white shadow-sm"
                      : isToday
                      ? "border border-[var(--accent)] text-[var(--accent)]"
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)]"
                  }`}
                >
                  {d.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
