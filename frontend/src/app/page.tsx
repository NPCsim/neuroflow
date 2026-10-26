"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Calendar as CalendarIcon,
  Clock,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  LayoutGrid,
  CalendarDays,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Layers,
  BarChart3,
  Target,
  Sliders,
  Shield,
  Zap,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

import { WorkloadBanner } from "@/components/plan/WorkloadBanner";
import { ProblemsSection } from "@/components/plan/ProblemsSection";
import { DayTimeline } from "@/components/plan/DayTimeline";
import { WeekTimeline } from "@/components/plan/WeekTimeline";
import { BlockDetailModal } from "@/components/plan/BlockDetailModal";
import { AskNeuroFlowPanel } from "@/components/plan/AskNeuroFlowPanel";
import { UndoToast } from "@/components/plan/UndoToast";
import { DemoBanner } from "@/components/plan/DemoBanner";
import { Toast } from "@/components/design-system/Toast";
import { ScrollReveal } from "@/components/design-system/ScrollReveal";
import {
  ScheduleOverviewData,
  ScheduleBlockItem,
  RemedyOption,
} from "@/components/plan/types";

export default function LandingPlanPage() {
  const [scheduleData, setScheduleData] = useState<ScheduleOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [replanning, setReplanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // View state
  const [isMounted, setIsMounted] = useState(false);
  const [viewMode, setViewMode] = useState<"day" | "week">("day");
  const [selectedDate, setSelectedDate] = useState<string>("2026-10-26");

  // Modal & Toast state
  const [selectedBlock, setSelectedBlock] = useState<ScheduleBlockItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string>("");
  const [toastType, setToastType] = useState<"success" | "error" | "info">("success");
  const [isToastOpen, setIsToastOpen] = useState(false);

  // Undo Proposal State
  const [undoSnapshotId, setUndoSnapshotId] = useState<string | null>(null);
  const [isUndoToastOpen, setIsUndoToastOpen] = useState(false);
  const [undoToastMessage, setUndoToastMessage] = useState("");
  const [isUndoing, setIsUndoing] = useState(false);

  // Demo Mode State (?demo=1)
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [scriptedCommandTrigger, setScriptedCommandTrigger] = useState<{
    command: string;
    timestamp: number;
  } | null>(null);

  const timelineRef = useRef<HTMLDivElement | null>(null);
  const apiUrl = API_BASE_URL;

  const showToast = (message: string, type: "success" | "error" | "info" = "success") => {
    setToastMessage(message);
    setToastType(type);
    setIsToastOpen(true);
  };

  const handleApplyProposalSuccess = (snapshotId: string, summary: string) => {
    setUndoSnapshotId(snapshotId);
    setUndoToastMessage(
      summary
        ? `Applied: "${summary.slice(0, 42)}..."`
        : "Plan proposal applied to schedule."
    );
    setIsUndoToastOpen(true);
  };

  const handleUndoProposal = async () => {
    try {
      setIsUndoing(true);
      const url = undoSnapshotId
        ? `${apiUrl}/agent/undo/${undoSnapshotId}`
        : `${apiUrl}/agent/undo`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snapshot_id: undoSnapshotId }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to undo plan proposal.");
      }

      setIsUndoToastOpen(false);
      setUndoSnapshotId(null);
      showToast("Changes reverted to prior schedule baseline.", "success");
      await fetchSchedule();
    } catch (err: any) {
      console.error("Undo proposal error:", err);
      showToast(err?.message || "Failed to revert proposal.", "error");
    } finally {
      setIsUndoing(false);
    }
  };

  // Fetch full schedule overview (supports ?now anchor for demo mode)
  const fetchSchedule = useCallback(async (demoOverride?: boolean) => {
    try {
      setLoading(true);
      setError(null);

      const activeDemo = demoOverride !== undefined ? demoOverride : isDemoMode;
      const queryParams = new URLSearchParams({ horizon_days: "7" });
      if (activeDemo) {
        queryParams.set("now", "2026-10-26T09:00:00Z");
      }

      const res = await fetch(`${apiUrl}/schedule?${queryParams.toString()}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        throw new Error(`Failed to load schedule (${res.status})`);
      }

      const data: ScheduleOverviewData = await res.json();
      setScheduleData(data);

      if (activeDemo) {
        setSelectedDate("2026-10-26");
      } else if (!selectedDate && data.today?.date) {
        setSelectedDate(data.today.date);
      } else if (!selectedDate && data.current_time) {
        setSelectedDate(data.current_time.slice(0, 10));
      }
    } catch (err: any) {
      console.error("Failed to load schedule:", err);
      setError(err?.message || "Could not connect to scheduler backend.");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, isDemoMode, selectedDate]);

  useEffect(() => {
    setIsMounted(true);
    let demoActive = false;
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      demoActive = params.get("demo") === "1";
      setIsDemoMode(demoActive);
    }
    if (demoActive) {
      setSelectedDate("2026-10-26");
    } else {
      setSelectedDate(new Date().toISOString().slice(0, 10));
    }
    fetchSchedule(demoActive);
  }, []);

  // Demo actions
  const handleToggleDemoMode = () => {
    const nextMode = !isDemoMode;
    setIsDemoMode(nextMode);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (nextMode) {
        url.searchParams.set("demo", "1");
      } else {
        url.searchParams.delete("demo");
      }
      window.history.replaceState({}, "", url.toString());
    }
    if (nextMode) {
      setSelectedDate("2026-10-26");
    }
    fetchSchedule(nextMode);
  };

  const handleResetDemo = async () => {
    try {
      const res = await fetch(`${apiUrl}/demo/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        throw new Error("Failed to reset demo workspace.");
      }
      const data = await res.json();
      showToast(
        data.message || "Seeded workspace loaded at fixed now (Oct 26, 9:00 AM).",
        "success"
      );
      setSelectedDate("2026-10-26");
      await fetchSchedule(true);
    } catch (err: any) {
      console.error("Demo reset error:", err);
      showToast(err?.message || "Failed to reset demo workspace.", "error");
    }
  };

  const handleSimulateEndOfDay = async () => {
    try {
      const res = await fetch(`${apiUrl}/demo/simulate-end-of-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horizon_days: 7 }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to simulate end of day.");
      }
      const data = await res.json();
      showToast(
        data.message || "Simulated 5:00 PM: Rollover complete and missed work processed.",
        "success"
      );
      await fetchSchedule(true);
    } catch (err: any) {
      console.error("Simulate EOD error:", err);
      showToast(err?.message || "Failed to simulate end of day.", "error");
    }
  };

  const handleRunScriptedCommand = (cmd: string) => {
    setScriptedCommandTrigger({ command: cmd, timestamp: Date.now() });
    showToast(`Executing scripted command: "${cmd}"`, "info");
  };

  // Handle "Replan now" rollover call
  const handleReplan = async () => {
    try {
      setReplanning(true);
      const res = await fetch(`${apiUrl}/schedule/rollover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horizon_days: 7 }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to run schedule rollover.");
      }

      const rolloverRes = await res.json();
      showToast(
        rolloverRes.message || "Schedule rolled over successfully.",
        "success"
      );
      await fetchSchedule();
    } catch (err: any) {
      console.error("Replan error:", err);
      showToast(err?.message || "Failed to run schedule rollover.", "error");
    } finally {
      setReplanning(false);
    }
  };

  // Handle remedy application
  const handleApplyRemedy = async (remedy: RemedyOption) => {
    try {
      const res = await fetch(`${apiUrl}/workload/remedy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: remedy.action,
          task_id: remedy.task_id,
          parameters: remedy.parameters || {},
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to apply remedy.");
      }

      showToast(`Remedy applied: "${remedy.title}"`, "success");
      await fetchSchedule();
    } catch (err: any) {
      console.error("Apply remedy error:", err);
      showToast(err?.message || "Failed to apply remedy.", "error");
    }
  };

  // Drag-and-drop reschedule with backend revalidation
  const handleDropReschedule = async (blockId: string, newStartIso: string) => {
    try {
      const res = await fetch(`${apiUrl}/schedule/blocks/${blockId}/reschedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_start_time: newStartIso }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        const errMsg = errJson.detail || "Reschedule conflict: exceeds capacity.";
        showToast(errMsg, "error");
        return;
      }

      showToast("Block rescheduled successfully.", "success");
      await fetchSchedule();
    } catch (err: any) {
      const msg = err?.message || "Failed to connect to rescheduling backend.";
      showToast(msg, "error");
    }
  };

  // Block modal opening
  const handleBlockClick = (block: ScheduleBlockItem) => {
    setSelectedBlock(block);
    setIsModalOpen(true);
  };

  // Date Navigation
  const handleNavigateDate = (direction: "prev" | "next" | "today") => {
    if (direction === "today") {
      const todayStr =
        scheduleData?.today?.date ||
        (scheduleData?.current_time ? scheduleData.current_time.slice(0, 10) : "") ||
        new Date().toISOString().slice(0, 10);
      setSelectedDate(todayStr);
      return;
    }

    const curr = new Date(selectedDate || new Date().toISOString().slice(0, 10));
    const deltaDays = viewMode === "week" ? 7 : 1;
    curr.setDate(curr.getDate() + (direction === "next" ? deltaDays : -deltaDays));
    setSelectedDate(curr.toISOString().slice(0, 10));
  };

  // Format header date string
  const getHeaderDateTitle = () => {
    if (!selectedDate) return "Today's Schedule";
    try {
      const d = new Date(`${selectedDate}T00:00:00`);
      if (viewMode === "day") {
        return d.toLocaleDateString("en-US", {
          weekday: "long",
          month: "short",
          day: "numeric",
        });
      } else {
        const weekEnd = new Date(d);
        weekEnd.setDate(weekEnd.getDate() + 6);
        return `${d.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        })} – ${weekEnd.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        })}`;
      }
    } catch {
      return selectedDate;
    }
  };

  const scrollToTimeline = () => {
    if (timelineRef.current) {
      timelineRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="w-full pb-28">
      {/* Demo Mode Banner (Active when ?demo=1 or toggled) */}
      <DemoBanner
        isDemoMode={isDemoMode}
        onResetDemo={handleResetDemo}
        onSimulateEndOfDay={handleSimulateEndOfDay}
        onRunScriptedCommand={handleRunScriptedCommand}
        onToggleDemoMode={handleToggleDemoMode}
        fixedNow="2026-10-26T09:00:00Z"
      />

      {/* =========================================================================
          HERO SECTION (Pure white in light mode, deep black in dark mode)
          Large centered headline: "Plan your day." / "Then actually do it."
         ========================================================================= */}
      <section className="bg-[var(--bg-primary)] pt-20 pb-24 sm:pt-28 sm:pb-32 px-6 transition-colors duration-200">
        <div className="max-w-[980px] mx-auto text-center space-y-6">
          <ScrollReveal>
            <h1 className="text-5xl sm:text-7xl md:text-8xl font-semibold tracking-[-0.03em] leading-[1.05] text-[var(--text-primary)]">
              <div>Plan your day.</div>
              <div>Then actually do it.</div>
            </h1>
          </ScrollReveal>

          <ScrollReveal delayMs={100}>
            <p className="text-lg sm:text-2xl text-[var(--text-secondary)] font-normal tracking-[-0.01em] max-w-2xl mx-auto leading-relaxed">
              Autonomous daily scheduling with strict capacity limits, natural language diffs, and instant rollbacks.
            </p>
          </ScrollReveal>

          <ScrollReveal delayMs={200}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <button
                onClick={scrollToTimeline}
                className="px-8 py-3.5 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-[15px] font-medium shadow-sm transition-all active:scale-95 cursor-pointer"
              >
                Start planning
              </button>

              <button
                onClick={scrollToTimeline}
                className="text-[15px] font-normal text-[var(--link)] hover:underline flex items-center gap-1 transition-all cursor-pointer"
              >
                <span>See how it works</span>
                <span className="text-lg leading-none">&gt;</span>
              </button>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* =========================================================================
          SECTION 1: Interactive Plan Timeline (#f5f5f7 in light, #161617 in dark)
          One big heading, one sentence, and clean interactive demo.
         ========================================================================= */}
      <section
        id="timeline"
        ref={timelineRef}
        className="bg-[var(--bg-secondary)] py-20 sm:py-28 px-4 sm:px-8 border-t border-b border-[var(--border-hairline)] transition-colors duration-200"
      >
        <div className="max-w-[1200px] mx-auto space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-[800px] mx-auto space-y-3">
            <ScrollReveal>
              <h2 className="text-3xl sm:text-5xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                The autonomous timeline.
              </h2>
            </ScrollReveal>
            <ScrollReveal delayMs={80}>
              <p className="text-base sm:text-xl text-[var(--text-secondary)] font-normal tracking-[-0.005em]">
                Every task is mathematically packed around fixed meetings and realistic buffers.
              </p>
            </ScrollReveal>
          </div>

          {/* Interactive Timeline Workspace */}
          <div className="space-y-6">
            {/* Workload Pulse Banner */}
            <WorkloadBanner
              workload={scheduleData?.workload}
              todayLoad={scheduleData?.today}
              onReplan={handleReplan}
              replanning={replanning}
            />

            {/* Bottlenecks / Problems Section */}
            {scheduleData?.workload?.problems && scheduleData.workload.problems.length > 0 && (
              <ProblemsSection
                problems={scheduleData.workload.problems}
                onApplyRemedy={handleApplyRemedy}
              />
            )}

            {/* Timeline Workspace Controls & Content */}
            <div className="apple-card p-6 space-y-6">
              {/* Timeline Header Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border-hairline)] pb-4">
                {/* Date Controls */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center rounded-full bg-[var(--fill-tertiary)] border border-[var(--border-hairline)] p-1">
                    <button
                      onClick={() => handleNavigateDate("prev")}
                      aria-label="Previous day or week"
                      className="p-1.5 rounded-full hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleNavigateDate("today")}
                      className="px-3 py-1 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] rounded-full transition-colors cursor-pointer"
                    >
                      Today
                    </button>
                    <button
                      onClick={() => handleNavigateDate("next")}
                      aria-label="Next day or week"
                      className="p-1.5 rounded-full hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                      {getHeaderDateTitle()}
                    </h3>
                    <p className="text-[11px] text-[var(--text-secondary)]">
                      {viewMode === "day" ? "Hourly focus intervals" : "7-day commitment horizon"}
                    </p>
                  </div>
                </div>

                {/* View Switcher & Refresh */}
                <div className="flex items-center gap-3">
                  {/* Segmented Control */}
                  <div className="flex items-center p-1 rounded-full bg-[var(--fill-tertiary)] border border-[var(--border-hairline)] text-xs">
                    <button
                      onClick={() => setViewMode("day")}
                      className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer ${
                        viewMode === "day"
                          ? "bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm"
                          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      }`}
                    >
                      Day View
                    </button>
                    <button
                      onClick={() => setViewMode("week")}
                      className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer ${
                        viewMode === "week"
                          ? "bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm"
                          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                      }`}
                    >
                      Week View
                    </button>
                  </div>

                  <button
                    onClick={() => fetchSchedule()}
                    disabled={loading}
                    aria-label="Refresh schedule"
                    className="p-2 rounded-full border border-[var(--border-hairline)] hover:bg-[var(--fill-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer disabled:opacity-40"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[var(--accent)]" : ""}`} />
                  </button>
                </div>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between text-xs text-rose-500">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                  <button onClick={() => fetchSchedule()} className="underline font-semibold ml-2">
                    Retry
                  </button>
                </div>
              )}

              {/* Day Timeline */}
              {viewMode === "day" && (
                <DayTimeline
                  selectedDate={selectedDate || "2026-10-26"}
                  blocks={scheduleData?.blocks || []}
                  fixedEvents={scheduleData?.fixed_events || []}
                  onBlockClick={handleBlockClick}
                  onDropReschedule={handleDropReschedule}
                  workStartTime="09:00"
                  workEndTime="17:00"
                />
              )}

              {/* Week Timeline */}
              {viewMode === "week" && (
                <WeekTimeline
                  dailyLoads={scheduleData?.workload?.daily_loads || []}
                  blocks={scheduleData?.blocks || []}
                  fixedEvents={scheduleData?.fixed_events || []}
                  onBlockClick={handleBlockClick}
                  onDropReschedule={handleDropReschedule}
                  onSelectDay={(d) => {
                    setSelectedDate(d);
                    setViewMode("day");
                  }}
                  selectedDate={selectedDate}
                />
              )}
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION 2: Natural Language Rescheduling (#ffffff in light, #000000 in dark)
          One big heading, one sentence, and clean visual demo.
         ========================================================================= */}
      <section className="bg-[var(--bg-primary)] py-20 sm:py-28 px-4 sm:px-8 transition-colors duration-200">
        <div className="max-w-[1200px] mx-auto space-y-12">
          <div className="text-center max-w-[800px] mx-auto space-y-3">
            <ScrollReveal>
              <h2 className="text-3xl sm:text-5xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                Natural language rescheduling.
              </h2>
            </ScrollReveal>
            <ScrollReveal delayMs={80}>
              <p className="text-base sm:text-xl text-[var(--text-secondary)] font-normal tracking-[-0.005em]">
                Tell NeuroFlow when plans change. Review visual diffs before applying.
              </p>
            </ScrollReveal>
          </div>

          {/* Interactive Feature Demo Card */}
          <ScrollReveal delayMs={150}>
            <div className="apple-card p-8 sm:p-12 max-w-4xl mx-auto space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                <div className="space-y-2 p-5 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)]">
                  <div className="w-8 h-8 rounded-full bg-[var(--cat-blue-bg)] text-[var(--accent)] flex items-center justify-center">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Spotlight command bar</h4>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Float at the bottom of your screen. Type or speak commands like &ldquo;I only have 3 hours today&rdquo;.
                  </p>
                </div>

                <div className="space-y-2 p-5 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)]">
                  <div className="w-8 h-8 rounded-full bg-[var(--cat-purple-bg)] text-[var(--cat-purple-text)] flex items-center justify-center">
                    <Layers className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Staged diff bottom sheet</h4>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Inspect exactly which blocks move, defer, or flag risks before writing changes to the database.
                  </p>
                </div>

                <div className="space-y-2 p-5 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)]">
                  <div className="w-8 h-8 rounded-full bg-[var(--cat-green-bg)] text-[var(--cat-green-text)] flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">One-tap instant rollback</h4>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Every applied proposal creates a snapshot. Revert anytime with a floating Undo pill.
                  </p>
                </div>
              </div>

              {/* Demo Sample Pill */}
              <div className="p-4 rounded-full apple-glass border border-[var(--border-hairline)] shadow-sm flex items-center justify-between gap-3 max-w-md mx-auto text-xs">
                <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                  <Sparkles className="w-4 h-4 text-[var(--accent)]" />
                  <span className="truncate">&ldquo;Something urgent came up, postpone writing&rdquo;</span>
                </div>
                <span className="px-3 py-1 rounded-full bg-[var(--accent)] text-white text-[11px] font-medium shrink-0">
                  Try below ↓
                </span>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* =========================================================================
          SECTION 3: Goals Decomposed into Focus (#f5f5f7 in light, #161617 in dark)
          One big heading, one sentence, and clean visual demo.
         ========================================================================= */}
      <section className="bg-[var(--bg-secondary)] py-20 sm:py-28 px-4 sm:px-8 border-t border-b border-[var(--border-hairline)] transition-colors duration-200">
        <div className="max-w-[1200px] mx-auto space-y-12">
          <div className="text-center max-w-[800px] mx-auto space-y-3">
            <ScrollReveal>
              <h2 className="text-3xl sm:text-5xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                From ambitions to focus blocks.
              </h2>
            </ScrollReveal>
            <ScrollReveal delayMs={80}>
              <p className="text-base sm:text-xl text-[var(--text-secondary)] font-normal tracking-[-0.005em]">
                Break complex milestones into prioritized, non-overlapping work sessions.
              </p>
            </ScrollReveal>
          </div>

          <ScrollReveal delayMs={150}>
            <div className="apple-card p-8 sm:p-12 max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="space-y-4 max-w-md text-left">
                <div className="w-10 h-10 rounded-2xl bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)] flex items-center justify-center">
                  <Target className="w-5 h-5" />
                </div>
                <h3 className="text-xl sm:text-2xl font-semibold text-[var(--text-primary)] tracking-tight">
                  Goal Decomposition Engine
                </h3>
                <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
                  Provide your target objectives and deadlines. NeuroFlow recursively breaks them down with duration estimates, prerequisite chains, and importance weights.
                </p>
                <div className="pt-2">
                  <Link
                    href="/goals"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--link)] hover:underline"
                  >
                    <span>Manage your goals and decomposed tasks</span>
                    <span>&gt;</span>
                  </Link>
                </div>
              </div>

              {/* Sample Visual Mini Cards */}
              <div className="w-full md:w-80 space-y-2.5">
                <div className="p-3.5 rounded-xl pastel-blue text-xs flex items-center justify-between">
                  <span className="font-semibold text-[var(--text-primary)]">Launch NeuroFlow MVP</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--cat-blue-bg)]">4 tasks</span>
                </div>
                <div className="p-3.5 rounded-xl pastel-purple text-xs flex items-center justify-between">
                  <span className="font-semibold text-[var(--text-primary)]">Customer Discovery</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--cat-purple-bg)]">3 tasks</span>
                </div>
                <div className="p-3.5 rounded-xl pastel-green text-xs flex items-center justify-between">
                  <span className="font-semibold text-[var(--text-primary)]">Platform Resilience</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--cat-green-bg)]">2 tasks</span>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* =========================================================================
          SECTION 4: Insights Grounded in Reality (#ffffff in light, #000000 in dark)
          One big heading, one sentence, and clean visual demo.
         ========================================================================= */}
      <section className="bg-[var(--bg-primary)] py-20 sm:py-28 px-4 sm:px-8 transition-colors duration-200">
        <div className="max-w-[1200px] mx-auto space-y-12">
          <div className="text-center max-w-[800px] mx-auto space-y-3">
            <ScrollReveal>
              <h2 className="text-3xl sm:text-5xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                Insights grounded in reality.
              </h2>
            </ScrollReveal>
            <ScrollReveal delayMs={80}>
              <p className="text-base sm:text-xl text-[var(--text-secondary)] font-normal tracking-[-0.005em]">
                Track completion rates, planned vs actual durations, and capacity heatmaps.
              </p>
            </ScrollReveal>
          </div>

          <ScrollReveal delayMs={150}>
            <div className="apple-card p-8 sm:p-12 max-w-4xl mx-auto space-y-8">
              {/* Stat Cards with Large Numbers & Small Gray Labels */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-left">
                <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
                  <span className="text-xs font-normal text-[var(--text-secondary)] uppercase tracking-wider">
                    Adherence
                  </span>
                  <div className="text-4xl sm:text-5xl font-light text-[var(--text-primary)] tracking-tight">
                    83%
                  </div>
                  <p className="text-[11px] text-emerald-500 font-medium">+5.2% vs baseline</p>
                </div>

                <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
                  <span className="text-xs font-normal text-[var(--text-secondary)] uppercase tracking-wider">
                    Focus Hours
                  </span>
                  <div className="text-4xl sm:text-5xl font-light text-[var(--text-primary)] tracking-tight">
                    24.5
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)]">Across 4 categories</p>
                </div>

                <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
                  <span className="text-xs font-normal text-[var(--text-secondary)] uppercase tracking-wider">
                    Ratio
                  </span>
                  <div className="text-4xl sm:text-5xl font-light text-[var(--text-primary)] tracking-tight">
                    1.06x
                  </div>
                  <p className="text-[11px] text-amber-500 font-medium">Mild buffer overrun</p>
                </div>

                <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
                  <span className="text-xs font-normal text-[var(--text-secondary)] uppercase tracking-wider">
                    Realism
                  </span>
                  <div className="text-4xl sm:text-5xl font-light text-[var(--text-primary)] tracking-tight">
                    88
                  </div>
                  <p className="text-[11px] text-emerald-500 font-medium">Optimal buffer health</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[var(--border-hairline)]">
                <span className="text-xs text-[var(--text-secondary)]">
                  Derived directly from activity logs and verified solver intervals.
                </span>
                <Link
                  href="/insights"
                  className="px-5 py-2.5 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-medium shadow-sm transition-all"
                >
                  View full analytics dashboard &gt;
                </Link>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* Floating Spotlight Command Bar */}
      <AskNeuroFlowPanel
        onApplySuccess={handleApplyProposalSuccess}
        onUndoApplied={handleUndoProposal}
        onScheduleRefresh={() => fetchSchedule()}
        apiUrl={apiUrl}
        showToast={showToast}
        demoMode={isDemoMode}
        externalCommandTrigger={scriptedCommandTrigger}
      />

      {/* Block Detail Modal */}
      {selectedBlock && (
        <BlockDetailModal
          isOpen={isModalOpen}
          block={selectedBlock}
          onClose={() => setIsModalOpen(false)}
          onUpdateStatus={async (blockId: string, status: "completed" | "missed" | "planned") => {
            try {
              await fetch(`${apiUrl}/schedule/blocks/${blockId}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status }),
              });
            } catch (e) {
              console.error(e);
            }
            await fetchSchedule();
          }}
          onReschedule={async (blockId: string, newStartIso: string) => {
            await handleDropReschedule(blockId, newStartIso);
            return { success: true };
          }}
        />
      )}

      {/* Undo Toast */}
      <UndoToast
        isOpen={isUndoToastOpen}
        onUndo={handleUndoProposal}
        onClose={() => setIsUndoToastOpen(false)}
        message={undoToastMessage}
        isUndoing={isUndoing}
      />

      {/* General Toast */}
      <Toast
        isOpen={isToastOpen}
        onClose={() => setIsToastOpen(false)}
        message={toastMessage}
        type={toastType}
      />
    </div>
  );
}
