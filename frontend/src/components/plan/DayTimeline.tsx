"use client";

import React, { useState } from "react";
import {
  Clock,
  Lock,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  GripVertical,
  Layers,
  Sparkles,
  Calendar,
} from "lucide-react";
import { ScheduleBlockItem, FixedEventItem } from "./types";

interface DayTimelineProps {
  selectedDate: string; // YYYY-MM-DD
  blocks: ScheduleBlockItem[];
  fixedEvents: FixedEventItem[];
  onBlockClick: (block: ScheduleBlockItem) => void;
  onDropReschedule: (blockId: string, newStartIso: string) => Promise<void>;
  workStartTime?: string;
  workEndTime?: string;
}

export function DayTimeline({
  selectedDate,
  blocks,
  fixedEvents,
  onBlockClick,
  onDropReschedule,
  workStartTime = "09:00",
  workEndTime = "17:00",
}: DayTimelineProps) {
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null);
  const [dragOverSlot, setDragOverSlot] = useState<string | null>(null);

  // Filter blocks and fixed events for this date
  const dayBlocks = blocks.filter((b) => b.start_time.startsWith(selectedDate));
  const dayFixedEvents = fixedEvents.filter((fe) => fe.start_time.startsWith(selectedDate));

  // Sort chronologically
  dayBlocks.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  dayFixedEvents.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  // Generate hourly slots from 08:00 to 19:00
  const hours = Array.from({ length: 12 }, (_, i) => i + 8); // 8 to 19

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

  const handleDragOver = (e: React.DragEvent, slotKey: string) => {
    e.preventDefault();
    if (dragOverSlot !== slotKey) {
      setDragOverSlot(slotKey);
    }
  };

  const handleDragLeave = (e: React.DragEvent, slotKey: string) => {
    if (dragOverSlot === slotKey) {
      setDragOverSlot(null);
    }
  };

  const handleDrop = async (e: React.DragEvent, slotDateTimeIso: string) => {
    e.preventDefault();
    setDragOverSlot(null);
    const blockId = e.dataTransfer.getData("text/plain") || draggedBlockId;
    setDraggedBlockId(null);
    if (!blockId) return;

    await onDropReschedule(blockId, slotDateTimeIso);
  };

  return (
    <div className="space-y-4">
      {/* Legend & Working Window Info */}
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

        <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>Work Window: {workStartTime} – {workEndTime}</span>
          <span>• Drag block to reschedule</span>
        </div>
      </div>

      {/* Hourly Timeline Grid */}
      <div className="space-y-3">
        {hours.map((hour) => {
          const hourStr = String(hour).padStart(2, "0") + ":00";
          const slotIso = `${selectedDate}T${hourStr}:00Z`;
          const displayTime = new Date(`${selectedDate}T${hourStr}:00`).toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
          });

          // Match blocks starting in this hour (e.g. 09:00 - 09:59)
          const matchingBlocks = dayBlocks.filter((b) => {
            const bStart = new Date(b.start_time);
            return bStart.getHours() === hour;
          });

          // Match fixed events in this hour
          const matchingFixed = dayFixedEvents.filter((fe) => {
            const feStart = new Date(fe.start_time);
            return feStart.getHours() === hour;
          });

          const isInsideWorkingHours =
            hourStr >= workStartTime && hourStr < workEndTime;

          const isOver = dragOverSlot === slotIso;

          return (
            <div
              key={hour}
              onDragOver={(e) => handleDragOver(e, slotIso)}
              onDragLeave={(e) => handleDragLeave(e, slotIso)}
              onDrop={(e) => handleDrop(e, slotIso)}
              className={`group flex items-start gap-4 p-3 rounded-2xl transition-all border ${
                isOver
                  ? "border-[var(--accent)] bg-[var(--cat-blue-bg)] scale-[1.01]"
                  : isInsideWorkingHours
                  ? "border-[var(--border-hairline)] bg-[var(--bg-secondary)]/30 hover:bg-[var(--bg-secondary)]/60"
                  : "border-transparent bg-transparent opacity-50"
              }`}
            >
              {/* Hour Label */}
              <div className="w-20 shrink-0 text-right pt-2 font-mono text-xs">
                <span className={isInsideWorkingHours ? "font-semibold text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}>
                  {displayTime}
                </span>
                <p className="text-[10px] text-[var(--text-secondary)]">
                  {isInsideWorkingHours ? "Work slot" : "Off hours"}
                </p>
              </div>

              {/* Vertical line indicator */}
              <div
                className={`w-0.5 self-stretch rounded-full transition-colors ${
                  isOver
                    ? "bg-[var(--accent)]"
                    : isInsideWorkingHours
                    ? "bg-[var(--border-subtle)]"
                    : "bg-transparent"
                }`}
              />

              {/* Slots Content Area */}
              <div className="flex-1 space-y-2.5 min-w-0">
                {/* 1. Fixed Events (Gray) */}
                {matchingFixed.map((fe) => {
                  const sTime = new Date(fe.start_time).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  });
                  const eTime = new Date(fe.end_time).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  });
                  const dur = Math.round(
                    (new Date(fe.end_time).getTime() - new Date(fe.start_time).getTime()) / 60000
                  );

                  return (
                    <div
                      key={fe.id}
                      className="p-3.5 rounded-2xl pastel-gray flex items-start justify-between gap-3 select-none"
                    >
                      <div className="flex items-start gap-2.5">
                        <div className="p-1 rounded-md bg-[var(--fill-tertiary)] text-[var(--text-secondary)] shrink-0 mt-0.5">
                          <Lock className="w-3.5 h-3.5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-semibold text-[var(--text-primary)]">
                              {fe.title}
                            </h4>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--fill-tertiary)] text-[var(--text-secondary)]">
                              Fixed Event
                            </span>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5 font-mono">
                            {sTime} – {eTime} ({dur}m) • Non-movable calendar block
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* 2. Scheduled Blocks (Color coded by goal, at risk flagged in red) */}
                {matchingBlocks.map((block) => {
                  const styles = getGoalColorClass(block.goal_color, block.is_at_risk);
                  const sTime = new Date(block.start_time).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  });
                  const eTime = new Date(block.end_time).toLocaleTimeString("en-US", {
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
                      className={`p-3.5 rounded-2xl border ${styles.card} transition-all cursor-pointer group/block relative overflow-hidden apple-card-hover`}
                    >
                      {/* Left accent color bar */}
                      <div
                        className={`absolute left-0 top-0 bottom-0 w-1 ${styles.accentBar}`}
                      />

                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5 min-w-0">
                          {/* Drag handle */}
                          <div
                            aria-label="Drag to reschedule"
                            className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] shrink-0 mt-0.5 cursor-grab active:cursor-grabbing"
                          >
                            <GripVertical className="w-3.5 h-3.5" />
                          </div>

                          <div className="space-y-1 min-w-0">
                            {/* Title & Status Badges */}
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4
                                className="text-xs font-semibold truncate text-[var(--text-primary)]"
                              >
                                {block.title}
                              </h4>

                              {block.is_at_risk && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/25 text-rose-200 border border-rose-500/50 flex items-center gap-1 animate-pulse">
                                  <AlertTriangle className="w-3 h-3" />
                                  At-Risk
                                </span>
                              )}

                              {block.is_stuck && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/25 text-amber-200 border border-amber-500/50 flex items-center gap-1">
                                  <AlertCircle className="w-3 h-3" />
                                  Stuck
                                </span>
                              )}

                              {block.status === "completed" && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                  <CheckCircle2 className="w-3 h-3" />
                                  Done
                                </span>
                              )}

                              {block.status === "missed" && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                  Missed
                                </span>
                              )}
                            </div>

                            {/* Subtitle / Goal / Timing */}
                            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono flex-wrap">
                              <span>
                                {sTime} – {eTime} ({dur}m)
                              </span>
                              {block.goal_title && (
                                <>
                                  <span>•</span>
                                  <span
                                    className={`px-2 py-0.5 rounded-full border text-[10px] ${styles.badge}`}
                                  >
                                    {block.goal_title}
                                  </span>
                                </>
                              )}
                              {block.chunk_index && block.total_chunks > 1 && (
                                <>
                                  <span>•</span>
                                  <span className="text-[10px] text-slate-400">
                                    Chunk {block.chunk_index}/{block.total_chunks}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Right side prompt to click */}
                        <div className="shrink-0 text-right">
                          <span className="text-[11px] text-cyan-400 opacity-0 group-hover/block:opacity-100 transition-opacity">
                            Click to edit / move →
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* 3. Empty slot placeholder / Drop target */}
                {matchingBlocks.length === 0 && matchingFixed.length === 0 && (
                  <div
                    className={`py-3 px-4 rounded-xl border border-dashed transition-all flex items-center justify-between text-xs ${
                      isOver
                        ? "border-cyan-400 bg-cyan-500/10 text-cyan-300"
                        : "border-white/5 hover:border-white/15 text-slate-400"
                    }`}
                  >
                    <span className="font-mono">
                      {isOver
                        ? "Drop to reschedule block to this slot"
                        : isInsideWorkingHours
                        ? "Available focus capacity window (60m)"
                        : "Unscheduled time window"}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {hourStr}
                    </span>
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
