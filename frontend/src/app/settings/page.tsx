"use client";

import { useState } from "react";
import { Settings, Clock, Globe, Shield, Save, Check, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/components/design-system/ThemeProvider";
import { ScrollReveal } from "@/components/design-system/ScrollReveal";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [timezone, setTimezone] = useState("America/New_York");
  const [workStart, setWorkStart] = useState("09:00");
  const [workEnd, setWorkEnd] = useState("17:00");
  const [bufferMin, setBufferMin] = useState(10);
  const [minChunk, setMinChunk] = useState(30);
  const [maxChunk, setMaxChunk] = useState(120);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-[760px] mx-auto px-6 py-12 space-y-10">
      {/* Page Header */}
      <ScrollReveal>
        <div className="pb-2 border-b border-[var(--border-subtle)]">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--text-primary)]">
            Settings
          </h1>
          <p className="text-base text-[var(--text-secondary)] mt-1.5">
            Configure calendar boundaries, focus intervals, and app appearance.
          </p>
        </div>
      </ScrollReveal>

      {/* Appearance Section */}
      <ScrollReveal>
        <div className="apple-card p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Appearance
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Select your preferred visual style across all devices
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-1">
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`p-3.5 rounded-2xl border text-center transition-all flex flex-col items-center gap-2 cursor-pointer ${
                theme === "light"
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] shadow-sm"
                  : "border-[var(--border-subtle)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
              }`}
            >
              <Sun className="w-5 h-5" />
              <span className="text-xs font-medium">Light</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`p-3.5 rounded-2xl border text-center transition-all flex flex-col items-center gap-2 cursor-pointer ${
                theme === "dark"
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] shadow-sm"
                  : "border-[var(--border-subtle)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
              }`}
            >
              <Moon className="w-5 h-5" />
              <span className="text-xs font-medium">Dark</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("system")}
              className={`p-3.5 rounded-2xl border text-center transition-all flex flex-col items-center gap-2 cursor-pointer ${
                theme === "system"
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] shadow-sm"
                  : "border-[var(--border-subtle)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
              }`}
            >
              <Monitor className="w-5 h-5" />
              <span className="text-xs font-medium">Auto (system)</span>
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Scheduler & Temporal Boundaries */}
      <ScrollReveal>
        <div className="apple-card p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Temporal boundaries
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Physical calendar boundaries used by the deterministic scheduling engine
            </p>
          </div>

          {/* Timezone */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--text-primary)] flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-[var(--accent)]" />
              <span>Display timezone</span>
            </label>
            <p className="text-xs text-[var(--text-secondary)]">
              Database timestamps are stored in UTC. Your schedule timeline renders in this zone.
            </p>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] transition-colors"
            >
              <option value="America/New_York">Eastern Time (America/New_York, EDT/EST)</option>
              <option value="America/Chicago">Central Time (America/Chicago, CDT/CST)</option>
              <option value="America/Denver">Mountain Time (America/Denver, MDT/MST)</option>
              <option value="America/Los_Angeles">Pacific Time (America/Los_Angeles, PDT/PST)</option>
              <option value="Europe/London">London (Europe/London, GMT/BST)</option>
              <option value="UTC">Coordinated Universal Time (UTC)</option>
            </select>
          </div>

          <div className="h-px bg-[var(--border-subtle)]" />

          {/* Working Hours */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-[var(--text-primary)] flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[var(--accent)]" />
              <span>Daily working hours</span>
            </label>
            <p className="text-xs text-[var(--text-secondary)]">
              The scheduler strictly prevents placing tasks outside these bounds.
            </p>
            <div className="flex items-center gap-4">
              <div>
                <span className="text-[11px] text-[var(--text-secondary)] block mb-1">Start</span>
                <input
                  type="time"
                  value={workStart}
                  onChange={(e) => setWorkStart(e.target.value)}
                  className="px-3 py-2 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                />
              </div>
              <span className="text-[var(--text-secondary)] mt-5">to</span>
              <div>
                <span className="text-[11px] text-[var(--text-secondary)] block mb-1">End</span>
                <input
                  type="time"
                  value={workEnd}
                  onChange={(e) => setWorkEnd(e.target.value)}
                  className="px-3 py-2 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                />
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* Buffers & Focus Chunks */}
      <ScrollReveal>
        <div className="apple-card p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
              Focus & rest parameters
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Dynamic breathing room and chunking boundaries for deep work sessions
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-primary)]">Rest buffer</label>
              <p className="text-[11px] text-[var(--text-secondary)]">Minutes between blocks</p>
              <input
                type="number"
                value={bufferMin}
                onChange={(e) => setBufferMin(Number(e.target.value))}
                min={0}
                max={60}
                className="w-full px-3 py-2 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-primary)]">Min chunk size</label>
              <p className="text-[11px] text-[var(--text-secondary)]">Smallest split duration</p>
              <input
                type="number"
                value={minChunk}
                onChange={(e) => setMinChunk(Number(e.target.value))}
                min={15}
                max={120}
                className="w-full px-3 py-2 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-primary)]">Max chunk size</label>
              <p className="text-[11px] text-[var(--text-secondary)]">Max continuous focus</p>
              <input
                type="number"
                value={maxChunk}
                onChange={(e) => setMaxChunk(Number(e.target.value))}
                min={30}
                max={240}
                className="w-full px-3 py-2 rounded-xl bg-[var(--fill-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
          </div>

          {/* Action button: Primary pill button */}
          <div className="pt-2 flex items-center justify-end">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--accent)] hover:opacity-95 text-white font-medium text-xs shadow-sm transition-all cursor-pointer"
            >
              {saved ? <Check className="w-4 h-4 text-white" /> : <Save className="w-4 h-4" />}
              <span>{saved ? "Settings saved" : "Save changes"}</span>
            </button>
          </div>
        </div>
      </ScrollReveal>
    </div>
  );
}
