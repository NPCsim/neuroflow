"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Send,
  Mic,
  MicOff,
  X,
  Check,
  RotateCcw,
  AlertTriangle,
  ArrowRight,
  Clock,
  Calendar,
  Layers,
  ChevronDown,
  Loader2,
  Zap,
} from "lucide-react";
import {
  AgentCommandResponseData,
  PlanDiffPayload,
  PlanDiffMoved,
  PlanDiffDeferred,
  PlanDiffAtRisk,
  PlanDiffDropped,
} from "./types";
import { API_BASE_URL } from "@/lib/api";

interface AskNeuroFlowPanelProps {
  onApplySuccess: (snapshotId: string, summary: string) => void;
  onUndoApplied: () => void;
  onScheduleRefresh: () => Promise<void>;
  apiUrl?: string;
  showToast: (msg: string, type?: "success" | "error" | "info") => void;
  demoMode?: boolean;
  externalCommandTrigger?: { command: string; timestamp: number } | null;
}

export function AskNeuroFlowPanel({
  onApplySuccess,
  onUndoApplied,
  onScheduleRefresh,
  apiUrl = API_BASE_URL,
  showToast,
  demoMode = false,
  externalCommandTrigger = null,
}: AskNeuroFlowPanelProps) {
  const [command, setCommand] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);

  // Staged Proposal State
  const [stagedProposal, setStagedProposal] = useState<AgentCommandResponseData | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [isDiscarding, setIsDiscarding] = useState(false);

  const recognitionRef = useRef<any>(null);

  // Send command to backend
  const handleSendCommand = async (customPrompt?: string) => {
    const promptToSend = (customPrompt || command).trim();
    if (!promptToSend) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    setIsExecuting(true);
    try {
      const res = await fetch(`${apiUrl}/agent/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: promptToSend,
          demo_mode: demoMode || false,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to process agent command.");
      }

      const data: AgentCommandResponseData = await res.json();
      setStagedProposal(data);
      setCommand("");
      showToast("Schedule proposal staged. Review changes below.", "info");
    } catch (err: any) {
      console.error("Agent command error:", err);
      showToast(err?.message || "Failed to communicate with scheduler agent.", "error");
    } finally {
      setIsExecuting(false);
    }
  };

  // Handle external command triggers (e.g. from DemoBanner)
  useEffect(() => {
    if (externalCommandTrigger && externalCommandTrigger.command) {
      setCommand(externalCommandTrigger.command);
      handleSendCommand(externalCommandTrigger.command);
    }
  }, [externalCommandTrigger]);

  // Check Web Speech API availability on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
        try {
          const rec = new SpeechRecognition();
          rec.continuous = false;
          rec.interimResults = true;
          rec.lang = "en-US";

          rec.onresult = (event: any) => {
            let currentText = "";
            for (let i = 0; i < event.results.length; i++) {
              currentText += event.results[i][0].transcript;
            }
            setCommand(currentText);
          };

          rec.onerror = (event: any) => {
            console.warn("Speech recognition error:", event.error);
            setIsListening(false);
          };

          rec.onend = () => {
            setIsListening(false);
          };

          recognitionRef.current = rec;
        } catch (e) {
          console.warn("Speech recognition initialization failed:", e);
        }
      }
    }
  }, []);

  const toggleVoiceInput = () => {
    if (!speechSupported || !recognitionRef.current) {
      showToast("Web Speech API not supported in this browser.", "info");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
        showToast("Listening... speak your schedule instructions", "info");
      } catch (err) {
        console.error("Start speech error:", err);
      }
    }
  };

  // Quick Command Chips
  const quickChips = [
    { label: "I only have 3 hours today", prompt: "I only have 3 hours today" },
    { label: "Something urgent came up", prompt: "Something urgent came up, defer non-urgent tasks" },
    { label: "Make tomorrow lighter", prompt: "Make tomorrow lighter by shifting heavy tasks" },
  ];

  // Apply staged proposal
  const handleApplyProposal = async () => {
    if (!stagedProposal) return;
    setIsApplying(true);
    try {
      const res = await fetch(`${apiUrl}/agent/apply/${stagedProposal.snapshot_id}`, {
        method: "POST",
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to apply plan proposal.");
      }

      const snapId = stagedProposal.snapshot_id;
      const summaryText = stagedProposal.summary;

      setStagedProposal(null);
      await onScheduleRefresh();
      onApplySuccess(snapId, summaryText);
    } catch (err: any) {
      console.error("Apply proposal error:", err);
      showToast(err?.message || "Failed to apply plan proposal.", "error");
    } finally {
      setIsApplying(false);
    }
  };

  // Discard staged proposal
  const handleDiscardProposal = async () => {
    if (!stagedProposal) return;
    setIsDiscarding(true);
    try {
      await fetch(`${apiUrl}/agent/undo/${stagedProposal.snapshot_id}`, {
        method: "POST",
      }).catch(() => {});

      setStagedProposal(null);
      showToast("Staged proposal discarded. Active schedule remains intact.", "info");
    } catch (err: any) {
      console.error("Discard proposal error:", err);
    } finally {
      setIsDiscarding(false);
    }
  };

  const diffPayload: PlanDiffPayload = stagedProposal?.diff || {};
  const movedList: PlanDiffMoved[] = diffPayload.moved || [];
  const deferredList: PlanDiffDeferred[] = diffPayload.deferred || [];
  const atRiskList: PlanDiffAtRisk[] = diffPayload.at_risk || diffPayload["at-risk"] || [];
  const droppedList: PlanDiffDropped[] = diffPayload.dropped || [];

  const totalModifications =
    movedList.length + deferredList.length + atRiskList.length + droppedList.length;

  const formatIsoTime = (iso?: string | null) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return iso;
    }
  };

  return (
    <>
      {/* Floating Spotlight Command Bar */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-xl pointer-events-none">
        <div className="pointer-events-auto space-y-2">
          {/* Quick Command Chips */}
          <div className="flex items-center justify-center gap-1.5 overflow-x-auto pb-1 px-1 select-none">
            {quickChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setCommand(chip.prompt);
                  handleSendCommand(chip.prompt);
                }}
                disabled={isExecuting}
                className="shrink-0 text-[11px] font-normal px-3 py-1 rounded-full bg-[var(--bg-elevated)]/90 hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-hairline)] shadow-sm backdrop-blur-md transition-all active:scale-95 cursor-pointer"
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Spotlight Pill Input Bar */}
          <div className="relative rounded-full apple-glass border border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] p-1.5 flex items-center gap-2 transition-all focus-within:ring-2 focus-within:ring-[var(--accent)]">
            {/* Sparkles / Search Icon */}
            <div className="w-8 h-8 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center shrink-0 ml-1">
              <Sparkles className="w-4 h-4" />
            </div>

            {/* Input field */}
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendCommand();
                }
              }}
              disabled={isExecuting}
              placeholder={
                isListening
                  ? "Listening... speak now"
                  : "Ask NeuroFlow: e.g. 'I only have 3 hours today'..."
              }
              className="flex-1 bg-transparent border-none text-[13px] text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none px-1"
            />

            {/* Voice Input Button */}
            <button
              onClick={toggleVoiceInput}
              disabled={isExecuting}
              title={isListening ? "Stop listening" : "Voice input"}
              className={`p-2 rounded-full transition-all cursor-pointer ${
                isListening
                  ? "bg-rose-500 text-white shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--fill-tertiary)]"
              }`}
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            {/* Execute Pill Button */}
            <button
              onClick={() => handleSendCommand()}
              disabled={isExecuting || !command.trim()}
              className="px-4 py-2 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-medium transition-all shadow-sm active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center gap-1.5"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Planning...</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <Send className="w-3 h-3" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Smooth Bottom Sheet for Plan Diff */}
      {stagedProposal && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end">
          {/* Backdrop */}
          <div
            onClick={() => setStagedProposal(null)}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
          />

          {/* Bottom Sheet Container */}
          <div className="relative w-full max-w-4xl mx-auto rounded-t-[28px] bg-[var(--bg-elevated)] border-t border-[var(--border-hairline)] shadow-[var(--shadow-modal)] max-h-[85vh] flex flex-col z-10 animate-fade-rise backdrop-blur-2xl">
            {/* Drag handle */}
            <div className="w-12 h-1 rounded-full bg-[var(--border-subtle)] mx-auto mt-3 mb-1" />

            {/* Sheet Header */}
            <div className="px-6 py-4 border-b border-[var(--border-hairline)] flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold tracking-[-0.015em] text-[var(--text-primary)]">
                    Proposed schedule diff
                  </h3>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[var(--cat-blue-bg)] text-[var(--cat-blue-text)]">
                    {totalModifications} modification{totalModifications !== 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  Review deterministic schedule adjustments before committing
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleDiscardProposal}
                  disabled={isDiscarding || isApplying}
                  className="px-4 py-2 rounded-full border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--fill-tertiary)] transition-all cursor-pointer"
                >
                  Discard
                </button>
                <button
                  onClick={handleApplyProposal}
                  disabled={isApplying || isDiscarding}
                  className="px-5 py-2 rounded-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-medium shadow-sm transition-all cursor-pointer flex items-center gap-1.5"
                >
                  {isApplying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  <span>Apply plan</span>
                </button>
              </div>
            </div>

            {/* Sheet Body (Scrollable) */}
            <div className="p-6 overflow-y-auto space-y-5">
              {/* Natural Language Agent Summary */}
              <div className="p-4 rounded-[18px] bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
                <span className="text-[11px] font-medium text-[var(--accent)] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  Agent Reasoning
                </span>
                <p className="text-[13px] text-[var(--text-primary)] leading-relaxed">
                  &ldquo;{stagedProposal.summary}&rdquo;
                </p>
              </div>

              {/* Moved Tasks Section */}
              {movedList.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                    Moved focus blocks ({movedList.length})
                  </h4>
                  <div className="space-y-2">
                    {movedList.map((m, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl pastel-blue flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-semibold text-xs text-[var(--text-primary)]">
                            {m.title}
                          </div>
                          <div className="text-[11px] text-[var(--text-secondary)]">
                            {m.reason || "Shifted to accommodate availability"}
                          </div>
                        </div>
                        <div className="text-xs font-mono font-medium flex items-center gap-1.5 text-[var(--accent)] shrink-0">
                          <span>{formatIsoTime(m.from_start)}</span>
                          <ArrowRight className="w-3 h-3" />
                          <span>{formatIsoTime(m.to_start)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Deferred Tasks Section */}
              {deferredList.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                    Deferred tasks ({deferredList.length})
                  </h4>
                  <div className="space-y-2">
                    {deferredList.map((d, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl pastel-orange flex items-center justify-between gap-3 text-xs"
                      >
                        <div>
                          <div className="font-semibold text-[var(--text-primary)]">{d.title}</div>
                          <div className="text-[11px] text-[var(--text-secondary)]">
                            {d.reason || "Deferred to next available open slot"}
                          </div>
                        </div>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--cat-orange-bg)] text-[var(--cat-orange-text)] font-medium shrink-0">
                          Deferred
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* At-Risk Tasks Section */}
              {atRiskList.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                    New risks flagged ({atRiskList.length})
                  </h4>
                  <div className="space-y-2">
                    {atRiskList.map((r, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl pastel-pink flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                          <div>
                            <div className="font-semibold text-[var(--text-primary)]">{r.title}</div>
                            <div className="text-[11px] text-[var(--text-secondary)]">{r.reason}</div>
                          </div>
                        </div>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--cat-pink-bg)] text-[var(--cat-pink-text)] font-medium shrink-0">
                          At Risk
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {totalModifications === 0 && (
                <div className="text-center py-8 text-xs text-[var(--text-secondary)]">
                  No schedule blocks were modified by this proposal.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
