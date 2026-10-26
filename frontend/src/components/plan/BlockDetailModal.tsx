"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Clock,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  AlertOctagon,
  MoveRight,
  RefreshCw,
  Target,
  Layers,
  Flag,
  Loader2,
} from "lucide-react";
import { ScheduleBlockItem } from "./types";

interface BlockDetailModalProps {
  block: ScheduleBlockItem | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdateStatus: (blockId: string, status: "completed" | "missed" | "planned") => Promise<void>;
  onReschedule: (blockId: string, newStart: string, newEnd?: string) => Promise<{ success: boolean; error?: string }>;
}

export function BlockDetailModal({
  block,
  isOpen,
  onClose,
  onUpdateStatus,
  onReschedule,
}: BlockDetailModalProps) {
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);
  const [rescheduling, setRescheduling] = useState(false);
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);
  const [customDateTime, setCustomDateTime] = useState<string>("");

  useEffect(() => {
    if (block) {
      setRescheduleError(null);
      // Format start_time for datetime-local input
      try {
        const d = new Date(block.start_time);
        // format as YYYY-MM-DDTHH:mm
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        const hours = String(d.getHours()).padStart(2, "0");
        const minutes = String(d.getMinutes()).padStart(2, "0");
        setCustomDateTime(`${year}-${month}-${day}T${hours}:${minutes}`);
      } catch {
        setCustomDateTime("");
      }
    }
  }, [block]);

  if (!isOpen || !block) return null;

  const startDate = new Date(block.start_time);
  const endDate = new Date(block.end_time);
  const durationMinutes = Math.round((endDate.getTime() - startDate.getTime()) / 60000);

  const formattedStartTime = startDate.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  const formattedEndTime = endDate.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  const formattedDate = startDate.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  const handleStatusClick = async (status: "completed" | "missed" | "planned") => {
    setUpdatingStatus(status);
    setRescheduleError(null);
    try {
      await onUpdateStatus(block.id, status);
      onClose();
    } catch (err: any) {
      setRescheduleError(err?.message || "Failed to update block status.");
    } finally {
      setUpdatingStatus(null);
    }
  };

  const handleQuickShift = async (minutesToAdd: number, targetDaysAhead: number = 0, setHour?: number) => {
    setRescheduling(true);
    setRescheduleError(null);
    try {
      const newD = new Date(block.start_time);
      if (targetDaysAhead > 0) {
        newD.setDate(newD.getDate() + targetDaysAhead);
      }
      if (setHour !== undefined) {
        newD.setHours(setHour, 0, 0, 0);
      } else {
        newD.setMinutes(newD.getMinutes() + minutesToAdd);
      }
      const newIso = newD.toISOString();
      const res = await onReschedule(block.id, newIso);
      if (res.success) {
        onClose();
      } else if (res.error) {
        setRescheduleError(res.error);
      }
    } catch (err: any) {
      setRescheduleError(err?.message || "Rescheduling failed.");
    } finally {
      setRescheduling(false);
    }
  };

  const handleCustomReschedule = async () => {
    if (!customDateTime) return;
    setRescheduling(true);
    setRescheduleError(null);
    try {
      const newD = new Date(customDateTime);
      if (isNaN(newD.getTime())) {
        setRescheduleError("Please provide a valid date and time.");
        setRescheduling(false);
        return;
      }
      const newIso = newD.toISOString();
      const res = await onReschedule(block.id, newIso);
      if (res.success) {
        onClose();
      } else if (res.error) {
        setRescheduleError(res.error);
      }
    } catch (err: any) {
      setRescheduleError(err?.message || "Rescheduling failed.");
    } finally {
      setRescheduling(false);
    }
  };

  const getGoalColorStyle = (color?: string | null) => {
    switch (color?.toLowerCase()) {
      case "emerald":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "cyan":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
      case "amber":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "purple":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      case "pink":
        return "bg-pink-500/20 text-pink-300 border-pink-500/40";
      default:
        return "bg-indigo-500/20 text-indigo-300 border-indigo-500/40";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-md transition-opacity"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-lg bg-[var(--bg-elevated)] border border-[var(--border-hairline)] rounded-[24px] shadow-[var(--shadow-modal)] p-6 sm:p-7 text-left z-10 animate-fade-rise space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-[var(--border-hairline)] pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border border-transparent ${getGoalColorStyle(
                  block.goal_color
                )}`}
              >
                {block.goal_title || "General Objective"}
              </span>

              {block.chunk_index && block.total_chunks > 1 && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--fill-tertiary)] text-[var(--text-secondary)]">
                  Chunk {block.chunk_index} of {block.total_chunks}
                </span>
              )}

              {block.status === "completed" && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[var(--cat-green-bg)] text-[var(--cat-green-text)] flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  Completed
                </span>
              )}

              {block.status === "missed" && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)]">
                  Missed
                </span>
              )}
            </div>

            <h2 className="text-lg font-semibold text-[var(--text-primary)] tracking-[-0.015em] pt-1">
              {block.title}
            </h2>
          </div>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="w-8 h-8 rounded-full hover:bg-[var(--fill-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-center transition-colors shrink-0 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Warnings if At Risk or Stuck */}
        {block.is_at_risk && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-200">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Flagged At-Risk:</span> Task completion is tightly constrained or extends past its target deadline. Consider applying a remedy or moving this block earlier.
            </div>
          </div>
        )}

        {block.is_stuck && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-200">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Stuck Task Warning:</span> Carried over 3+ planning sessions without completion.
            </div>
          </div>
        )}

        {/* Timing & Meta Info */}
        <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/5 text-xs">
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
              <Calendar className="w-3 h-3 text-cyan-400" />
              Scheduled Date
            </span>
            <p className="font-medium text-slate-200">{formattedDate}</p>
          </div>

          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              Interval & Duration
            </span>
            <p className="font-medium text-slate-200">
              {formattedStartTime} – {formattedEndTime} ({durationMinutes}m)
            </p>
          </div>

          {block.deadline && (
            <div className="space-y-1 col-span-2 pt-1 border-t border-white/5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                <Flag className="w-3 h-3 text-rose-400" />
                Hard Deadline
              </span>
              <p className="font-mono text-slate-300">
                {new Date(block.deadline).toLocaleString("en-US", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </p>
            </div>
          )}
        </div>

        {/* Reschedule Error Alert (Backend Re-validation Error) */}
        {rescheduleError && (
          <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-xs text-rose-200 space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-rose-300">
              <AlertOctagon className="w-4 h-4 text-rose-400" />
              <span>Backend Re-validation Failed</span>
            </div>
            <p className="leading-relaxed pl-5">{rescheduleError}</p>
          </div>
        )}

        {/* Section 1: Mark Done / Missed / Planned */}
        <div className="space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Update Block Execution Status:
          </span>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleStatusClick("completed")}
              disabled={updatingStatus !== null}
              className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                block.status === "completed"
                  ? "bg-emerald-500 text-slate-950 font-bold"
                  : "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 border border-emerald-500/30"
              }`}
            >
              {updatingStatus === "completed" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              <span>Mark Done</span>
            </button>

            <button
              onClick={() => handleStatusClick("missed")}
              disabled={updatingStatus !== null}
              className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                block.status === "missed"
                  ? "bg-rose-500 text-white font-bold"
                  : "bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 border border-rose-500/30"
              }`}
            >
              {updatingStatus === "missed" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5" />
              )}
              <span>Mark Missed</span>
            </button>

            <button
              onClick={() => handleStatusClick("planned")}
              disabled={updatingStatus !== null}
              className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                block.status === "planned"
                  ? "bg-cyan-500 text-slate-950 font-bold"
                  : "bg-white/5 text-slate-300 hover:bg-white/10 border border-white/10"
              }`}
            >
              {updatingStatus === "planned" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              <span>Reset Planned</span>
            </button>
          </div>
        </div>

        {/* Section 2: Move / Reschedule Block */}
        <div className="space-y-2.5 pt-2 border-t border-white/5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>Move & Reschedule (Re-validates Backend)</span>
            <span className="text-[10px] font-normal text-slate-400">Strict conflict checks</span>
          </span>

          {/* Quick Reschedule Presets */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button
              onClick={() => handleQuickShift(30)}
              disabled={rescheduling}
              className="py-1.5 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] font-mono border border-white/5 transition-all cursor-pointer"
            >
              +30 mins
            </button>
            <button
              onClick={() => handleQuickShift(60)}
              disabled={rescheduling}
              className="py-1.5 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] font-mono border border-white/5 transition-all cursor-pointer"
            >
              +1 hour
            </button>
            <button
              onClick={() => handleQuickShift(0, 1)}
              disabled={rescheduling}
              className="py-1.5 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] font-mono border border-white/5 transition-all cursor-pointer"
            >
              Tomorrow
            </button>
            <button
              onClick={() => handleQuickShift(0, 1, 9)}
              disabled={rescheduling}
              className="py-1.5 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] font-mono border border-white/5 transition-all cursor-pointer"
            >
              Tmrw 09:00
            </button>
          </div>

          {/* Custom Date & Time Picker */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="datetime-local"
              value={customDateTime}
              onChange={(e) => setCustomDateTime(e.target.value)}
              className="flex-1 h-9 px-3 rounded-xl bg-white/5 border border-white/10 text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
            />
            <button
              onClick={handleCustomReschedule}
              disabled={rescheduling || !customDateTime}
              className="h-9 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-40"
            >
              {rescheduling ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <MoveRight className="w-3.5 h-3.5" />
              )}
              <span>Move</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
