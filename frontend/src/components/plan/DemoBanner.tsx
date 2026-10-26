"use client";

import React, { useState } from "react";
import {
  Sparkles,
  RotateCcw,
  Sunset,
  Clock,
  Zap,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Play,
  X,
  Layers,
} from "lucide-react";

interface DemoBannerProps {
  isDemoMode: boolean;
  onResetDemo: () => Promise<void>;
  onSimulateEndOfDay: () => Promise<void>;
  onRunScriptedCommand: (command: string) => void;
  onToggleDemoMode: () => void;
  fixedNow?: string;
}

export function DemoBanner({
  isDemoMode,
  onResetDemo,
  onSimulateEndOfDay,
  onRunScriptedCommand,
  onToggleDemoMode,
  fixedNow = "2026-10-26T09:00:00Z",
}: DemoBannerProps) {
  const [resetting, setResetting] = useState(false);
  const [simulating, setSimulating] = useState(false);

  const handleReset = async () => {
    try {
      setResetting(true);
      await onResetDemo();
    } finally {
      setResetting(false);
    }
  };

  const handleSimulate = async () => {
    try {
      setSimulating(true);
      await onSimulateEndOfDay();
    } finally {
      setSimulating(false);
    }
  };

  if (!isDemoMode) {
    return (
      <div className="bg-[var(--bg-elevated)] border-b border-[var(--border-hairline)] py-2 px-4 transition-all">
        <div className="max-w-[1200px] mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-[var(--text-secondary)]">
            <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span>Presenting or testing? Enable deterministic Demo Mode with fixed time and pre-cached LLM responses.</span>
          </div>
          <button
            onClick={onToggleDemoMode}
            className="px-3 py-1 rounded-full bg-[var(--accent)] text-white font-medium hover:bg-[var(--accent-hover)] transition-all cursor-pointer flex items-center gap-1.5 shadow-xs"
          >
            <span>Activate ?demo=1 mode</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="sticky top-12 z-40 bg-[var(--bg-elevated)]/95 dark:bg-purple-950/80 border-b border-purple-500/30 py-2.5 px-4 sm:px-6 backdrop-blur-xl shadow-md transition-all">
      <div className="max-w-[1200px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left: Indicator & Context */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400 dark:text-purple-300 shrink-0 shadow-[0_0_12px_-2px_rgba(168,85,247,0.4)]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-700 dark:text-purple-200 border border-purple-500/30">
                Demo Mode Active (?demo=1)
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-purple-700/80 dark:text-purple-300/80 font-mono">
                <Clock className="w-3 h-3" />
                Fixed: Mon Oct 26, 09:00 AM UTC
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Identical deterministic workspace every load • LLM responses pre-cached against rate limits
            </p>
          </div>
        </div>

        {/* Right: One-Click Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* One-click Reset Seeded Workspace */}
          <button
            id="btn-reset-demo"
            onClick={handleReset}
            disabled={resetting || simulating}
            className="px-3 py-1 rounded-full bg-purple-600/15 hover:bg-purple-600/25 text-purple-700 dark:text-purple-100 border border-purple-400/40 text-xs font-medium transition-all active:scale-95 cursor-pointer flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            title="Reloads the original seeded workspace anchored at fixed now (9:00 AM)"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? "animate-spin" : ""}`} />
            <span>{resetting ? "Resetting..." : "One-Click Seed Reset"}</span>
          </button>

          {/* Simulate End of Day Button */}
          <button
            id="btn-simulate-eod"
            onClick={handleSimulate}
            disabled={resetting || simulating}
            className="px-3 py-1 rounded-full bg-amber-500/15 hover:bg-amber-500/25 text-amber-700 dark:text-amber-200 border border-amber-500/40 text-xs font-medium transition-all active:scale-95 cursor-pointer flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            title="Advances time to 5:00 PM, marks today's uncompleted work missed, and triggers schedule rollover"
          >
            <Sunset className={`w-3.5 h-3.5 ${simulating ? "animate-spin" : ""}`} />
            <span>{simulating ? "Simulating..." : "Simulate End of Day"}</span>
          </button>

          {/* Exit Demo Mode */}
          <button
            onClick={onToggleDemoMode}
            className="p-1 rounded-full hover:bg-[var(--fill-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            title="Exit Demo Mode"
            aria-label="Exit Demo Mode"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scripted Demo Commands Strip */}
      <div className="max-w-[1200px] mx-auto mt-2 pt-1.5 border-t border-purple-500/15 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="text-purple-700/80 dark:text-purple-300/80 font-medium flex items-center gap-1">
          <Zap className="w-3 h-3 text-amber-500 dark:text-amber-300" />
          Pre-cached Commands:
        </span>
        <button
          id="btn-scripted-cmd-1"
          onClick={() => onRunScriptedCommand("I only have 3 hours today")}
          className="px-2.5 py-0.5 rounded-md bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-purple-700 dark:text-purple-200 hover:text-purple-900 dark:hover:text-white transition-all cursor-pointer font-mono"
        >
          &quot;I only have 3 hours today&quot;
        </button>
        <button
          id="btn-scripted-cmd-2"
          onClick={() => onRunScriptedCommand("Something urgent came up, defer non-urgent tasks")}
          className="px-2.5 py-0.5 rounded-md bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-purple-700 dark:text-purple-200 hover:text-purple-900 dark:hover:text-white transition-all cursor-pointer font-mono"
        >
          &quot;Something urgent came up&quot;
        </button>
        <button
          id="btn-scripted-cmd-3"
          onClick={() => onRunScriptedCommand("Make tomorrow lighter by shifting heavy tasks")}
          className="px-2.5 py-0.5 rounded-md bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-purple-700 dark:text-purple-200 hover:text-purple-900 dark:hover:text-white transition-all cursor-pointer font-mono"
        >
          &quot;Make tomorrow lighter&quot;
        </button>
      </div>
    </div>
  );
}
