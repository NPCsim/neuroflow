"use client";

import React, { useState } from "react";
import {
  Clock,
  Lock,
  AlertTriangle,
  CheckCircle2,
  GripVertical,
  Calendar,
  AlertOctagon,
} from "lucide-react";
import { ScheduleBlockItem, FixedEventItem, DayLoad } from "./types";

interface WeekTimelineProps {
  dailyLoads: DayLoad[];
  blocks: ScheduleBlockItem[];
  fixedEvents: FixedEventItem[];
  onBlockClick: (block: ScheduleBlockItem) => void;
  onDropReschedule: (blockId: string, newStartIso: string) => Promise<void>;
  onSelectDay: (date: string) => void;
  selectedDate: string;
}

export function WeekTimeline({
  dailyLoads,
  blocks,
  fixedEvents,
  onBlockClick,
  onDropReschedule,
  onSelectDay,
  selectedDate,
}: WeekTimelineProps) {
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null);
  const [dragOverDay, setDragOverDay] = useState<string | null>(null);

  const getGoalColorClass = (color?: string | null, isAtRisk?: boolean) => {
    if (isAtRisk) {
      return {
        card: "pastel-pink rounded-2xl shadow-sm border border-rose-500/30",
        badge: "bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]",
        accentBar: "bg-[var(--cat-pink-text)]",
        text: "text-[var(--text-primary)]",
      };
    }

    switch (color?.toLowerCase()) {
      case "emerald":
      case "green":
        return {
          card: "pastel-green rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-green-bg)] text-[var(--cat-green-text)]",
          accentBar: "bg-[var(--cat-green-text)]",
          text: "text-[var(--text-primary)]",
        };
      case "cyan":
      case "teal":
        return {
          card: "pastel-teal rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-teal-bg)] text-[var(--cat-teal-text)]",
          accentBar: "bg-[var(--cat-teal-text)]",
          text: "text-[var(--text-primary)]",
        };
      case "amber":
      case "orange":
        return {
          card: "pastel-orange rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)]",
          accentBar: "bg-[var(--cat-orange-text)]",
          text: "text-[var(--text-primary)]",
        };
      case "purple":
      case "violet":
        return {
          card: "pastel-purple rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-purple-bg)] text-[var(--cat-purple-text)]",
          accentBar: "bg-[var(--cat-purple-text)]",
          text: "text-[var(--text-primary)]",
        };
      case "pink":
        return {
          card: "pastel-pink rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]",
          accentBar: "bg-[var(--cat-pink-text)]",
          text: "text-[var(--text-primary)]",
        };
      default:
        return {
          card: "pastel-blue rounded-2xl shadow-sm",
          badge: "bg-[var(--cat-blue-bg)] text-[var(--cat-blue-text)]",
          accentBar: "bg-[var(--cat-blue-text)]",
          text: "text-[var(--text-primary)]",
        };
    }
  };

  const handleDragStart = (e: React.DragEvent, blockId: string) => {
    e.dataTransfer.setData("text/plain", blockId);
    setDraggedBlockId(blockId);
  };

  const handleDragOver = (e: React.DragEvent, dateStr: string) => {
    e.preventDefault();
    if (dragOverDay !== dateStr) {
      setDragOverDay(dateStr);
    }
  };

  const handleDragLeave = (e: React.DragEvent, dateStr: string) => {
    if (dragOverDay === dateStr) {
      setDragOverDay(null);
    }
  };

  const handleDrop = async (e: React.DragEvent, dateStr: string) => {
    e.preventDefault();
    setDragOverDay(null);
    const blockId = e.dataTransfer.getData("text/plain") || draggedBlockId;
    setDraggedBlockId(null);
    if (!blockId) return;

    // Find original block time of day
    const origBlock = blocks.find((b) => b.id === blockId);
    let targetTime = "09:00:00Z";
    if (origBlock) {
      const origDate = new Date(origBlock.start_time);
      const hours = String(origDate.getUTCHours()).padStart(2, "0");
      const minutes = String(origDate.getUTCMinutes()).padStart(2, "0");
      targetTime = `${hours}:${minutes}:00Z`;
    }

    const newIso = `${dateStr}T${targetTime}`;
    await onDropReschedule(blockId, newIso);
  };

  return (
    <div className="space-y-4">
      {/* Legend & Instructions */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 pb-1 border-b border-white/5">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-semibold text-slate-300">Legend:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
            <span className="text-[11px]">Goal Focus Blocks</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-500" />
            <span className="text-[11px] text-slate-300">Fixed Events (Gray)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-[11px] text-rose-300 font-semibold">At-Risk Tasks (Red)</span>
          </div>
        </div>

        <span className="text-[11px] text-slate-400 font-mono">
          Drag blocks between columns to reschedule across days
        </span>
      </div>

      {/* Week Columns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3.5 items-start">
        {dailyLoads.map((day) => {
          const dateStr = day.date;
          const isSelected = selectedDate === dateStr;
          const isOver = dragOverDay === dateStr;

          // Day items
          const dayBlocks = blocks.filter((b) => b.start_time.startsWith(dateStr));
          const dayFixed = fixedEvents.filter((fe) => fe.start_time.startsWith(dateStr));

          dayBlocks.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
          dayFixed.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

          const loadPct = Math.round(day.load_percentage);
          const isOverloaded = day.is_overloaded || loadPct > 100;

          return (
            <div
              key={dateStr}
              onDragOver={(e) => handleDragOver(e, dateStr)}
              onDragLeave={(e) => handleDragLeave(e, dateStr)}
              onDrop={(e) => handleDrop(e, dateStr)}
              className={`rounded-2xl border transition-all flex flex-col p-3.5 space-y-3 min-h-[360px] ${
                isOver
                  ? "border-cyan-400 bg-cyan-500/10 shadow-[0_0_20px_-3px_rgba(6,182,212,0.3)]"
                  : isSelected
                  ? "border-indigo-500/50 bg-[#0e1424] shadow-lg shadow-indigo-500/10"
                  : "border-white/5 bg-slate-900/40 hover:border-white/10"
              }`}
            >
              {/* Day Column Header */}
              <div
                onClick={() => onSelectDay(dateStr)}
                className="cursor-pointer space-y-1.5 pb-2.5 border-b border-white/5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white tracking-tight">
                    {day.day_of_week}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                      isOverloaded
                        ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                        : loadPct > 80
                        ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                        : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    }`}
                  >
                    {loadPct}%
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span>{dateStr.slice(5)}</span>
                  <span>
                    {((day.scheduled_minutes + day.fixed_event_minutes) / 60).toFixed(1)}h /{" "}
                    {(day.capacity_minutes / 60).toFixed(1)}h
                  </span>
                </div>

                {/* Day load bar */}
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full ${
                      isOverloaded
                        ? "bg-rose-500"
                        : loadPct > 80
                        ? "bg-amber-500"
                        : "bg-cyan-400"
                    }`}
                    style={{ width: `${Math.min(loadPct, 100)}%` }}
                  />
                </div>
              </div>

              {/* Items List */}
              <div className="space-y-2 flex-1">
                {/* 1. Fixed Events (Gray) */}
                {dayFixed.map((fe) => {
                  const sTime = new Date(fe.start_time).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  });

                  return (
                    <div
                      key={fe.id}
                      className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 text-slate-300 text-xs space-y-1 select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <Lock className="w-3 h-3 text-slate-400 shrink-0" />
                        <h5 className="font-semibold text-slate-200 truncate text-[11px]">
                          {fe.title}
                        </h5>
                      </div>
                      <p className="text-[10px] text-slate-400 font-mono">{sTime} • Fixed</p>
                    </div>
                  );
                })}

                {/* 2. Scheduled Blocks */}
                {dayBlocks.map((block) => {
                  const styles = getGoalColorClass(block.goal_color, block.is_at_risk);
                  const sTime = new Date(block.start_time).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  });
                  const dur = Math.round(
                    (new Date(block.end_time).getTime() - new Date(block.start_time).getTime()) /
                      60000
                  );

                  return (
                    <div
                      key={block.id}
                      draggable={true}
                      onDragStart={(e) => handleDragStart(e, block.id)}
                      onClick={() => onBlockClick(block)}
                      className={`p-2.5 rounded-xl border ${styles.card} transition-all cursor-pointer group/block relative overflow-hidden space-y-1`}
                    >
                      <div
                        className={`absolute left-0 top-0 bottom-0 w-1 ${styles.accentBar}`}
                      />

                      <div className="pl-1.5 space-y-1">
                        <div className="flex items-center justify-between gap-1">
                          <h5
                            className={`font-semibold text-[11px] truncate ${styles.text} group-hover/block:text-white`}
                          >
                            {block.title}
                          </h5>
                          {block.is_at_risk && (
                            <AlertTriangle className="w-3 h-3 text-rose-400 shrink-0 animate-pulse" />
                          )}
                          {block.status === "completed" && (
                            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                          )}
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                          <span>{sTime}</span>
                          <span>{dur}m</span>
                        </div>

                        {block.goal_title && (
                          <div className="pt-0.5">
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded-full border truncate inline-block max-w-[120px] ${styles.badge}`}
                            >
                              {block.goal_title}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Empty State / Drop target */}
                {dayBlocks.length === 0 && dayFixed.length === 0 && (
                  <div className="h-28 rounded-xl border border-dashed border-white/5 flex flex-col items-center justify-center text-center p-3 text-[11px] text-slate-400">
                    <span>{isOver ? "Drop to move here" : "No scheduled work"}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
