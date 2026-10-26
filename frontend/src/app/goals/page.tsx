"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Target,
  Sparkles,
  Calendar,
  Clock,
  Trash2,
  Plus,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  HelpCircle,
  Layers,
  Send,
  RefreshCw,
} from "lucide-react";
import { ScrollReveal } from "@/components/design-system/ScrollReveal";
import { API_BASE_URL } from "@/lib/api";

interface DecomposedTask {
  id: string;
  title: string;
  est_minutes: number;
  importance: number;
  deadline?: string;
  depends_on?: number[];
  category?: string;
  rationale?: string;
}

interface DecomposedGoal {
  id: string;
  title: string;
  description: string;
  target_date?: string;
  tasks: DecomposedTask[];
}

export default function GoalsPage() {
  const [prompt, setPrompt] = useState(
    "Prepare for my DBMS exam in 10 days and finish my hackathon project"
  );
  const [decomposing, setDecomposing] = useState(false);
  const [savingAndScheduling, setSavingAndScheduling] = useState(false);
  const [clarificationNeeded, setClarificationNeeded] = useState(false);
  const [clarifyingQuestions, setClarifyingQuestions] = useState<string[]>([]);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<number, string>>({});
  const [goals, setGoals] = useState<DecomposedGoal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<{
    saved_goals_count: number;
    saved_tasks_count: number;
    scheduled_blocks_count?: number;
    message?: string;
  } | null>(null);

  const apiUrl = API_BASE_URL;

  // Handle Goal Decomposition
  const handleDecompose = async (customPrompt?: string) => {
    const textToSubmit = (customPrompt || prompt).trim();
    if (!textToSubmit) {
      setError("Please enter a goal description.");
      return;
    }

    setDecomposing(true);
    setError(null);
    setSaveSuccess(null);
    setClarificationNeeded(false);

    try {
      const res = await fetch(`${apiUrl}/goals/decompose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: textToSubmit }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Decomposition failed (HTTP ${res.status})`);
      }

      const data = await res.json();

      if (data.needs_clarification || data.status === "clarification_needed") {
        setClarificationNeeded(true);
        setClarifyingQuestions(data.clarifying_questions || []);
        setClarificationAnswers({});
        setGoals([]);
      } else {
        setClarificationNeeded(false);
        setClarifyingQuestions([]);
        setGoals(data.goals || []);
      }
    } catch (err: any) {
      setError(err.message || "Failed to decompose goal with AI");
    } finally {
      setDecomposing(false);
    }
  };

  // Submit Clarification Answers
  const handleClarificationSubmit = () => {
    const answersList = Object.entries(clarificationAnswers)
      .map(([idx, ans]) => `${clarifyingQuestions[Number(idx)]}: ${ans}`)
      .join(". ");

    const refinedPrompt = `${prompt.trim()}. Clarifications: ${answersList}`;
    setPrompt(refinedPrompt);
    handleDecompose(refinedPrompt);
  };

  // Edit Task Field
  const updateTaskField = (
    goalIdx: number,
    taskIdx: number,
    field: keyof DecomposedTask,
    value: any
  ) => {
    setGoals((prev) => {
      const next = [...prev];
      const g = { ...next[goalIdx] };
      const tasks = [...g.tasks];
      tasks[taskIdx] = { ...tasks[taskIdx], [field]: value };
      g.tasks = tasks;
      next[goalIdx] = g;
      return next;
    });
  };

  // Edit Goal Title
  const updateGoalField = (
    goalIdx: number,
    field: keyof DecomposedGoal,
    value: any
  ) => {
    setGoals((prev) => {
      const next = [...prev];
      next[goalIdx] = { ...next[goalIdx], [field]: value };
      return next;
    });
  };

  // Add Task to Goal
  const handleAddTask = (goalIdx: number) => {
    setGoals((prev) => {
      const next = [...prev];
      const g = { ...next[goalIdx] };
      const newTask: DecomposedTask = {
        id: `custom-task-${Date.now()}`,
        title: "New subtask",
        est_minutes: 60,
        importance: 3,
        deadline: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10),
        category: "engineering",
        rationale: "Added during review.",
        depends_on: [],
      };
      g.tasks = [...g.tasks, newTask];
      next[goalIdx] = g;
      return next;
    });
  };

  // Delete Task from Goal
  const handleDeleteTask = (goalIdx: number, taskIdx: number) => {
    setGoals((prev) => {
      const next = [...prev];
      const g = { ...next[goalIdx] };
      g.tasks = g.tasks.filter((_, idx) => idx !== taskIdx);
      next[goalIdx] = g;
      return next;
    });
  };

  // Save and Schedule Workflow
  const handleSaveAndSchedule = async () => {
    if (goals.length === 0) return;

    setSavingAndScheduling(true);
    setError(null);

    try {
      const saveRes = await fetch(`${apiUrl}/goals/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goals }),
      });

      if (!saveRes.ok) {
        const errJson = await saveRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Failed to save goals (HTTP ${saveRes.status})`);
      }

      const saveData = await saveRes.json();

      const rebuildRes = await fetch(`${apiUrl}/schedule/rebuild`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horizon_days: 7 }),
      });

      let scheduledBlocksCount = 0;
      if (rebuildRes.ok) {
        const rebuildData = await rebuildRes.json();
        scheduledBlocksCount = rebuildData.scheduled_blocks_count || 0;
      }

      setSaveSuccess({
        saved_goals_count: saveData.saved_goals_count || goals.length,
        saved_tasks_count: saveData.saved_tasks_count || 0,
        scheduled_blocks_count: scheduledBlocksCount,
        message: "Goals persisted and deterministic schedule placed successfully.",
      });
    } catch (err: any) {
      setError(err.message || "Failed to save goals and rebuild schedule");
    } finally {
      setSavingAndScheduling(false);
    }
  };

  const totalTasks = goals.reduce((acc, g) => acc + g.tasks.length, 0);
  const totalEstimatedMinutes = goals.reduce(
    (acc, g) => acc + g.tasks.reduce((tAcc, t) => tAcc + (Number(t.est_minutes) || 0), 0),
    0
  );
  const totalEstimatedHours = (totalEstimatedMinutes / 60).toFixed(1);

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-12 space-y-12">
      {/* Page Header */}
      <ScrollReveal>
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-2 border-b border-[var(--border-subtle)]">
          <div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--text-primary)]">
              Goal decomposition
            </h1>
            <p className="text-base text-[var(--text-secondary)] mt-1.5 max-w-2xl">
              Turn natural-language ambitions into atomic, splittable tasks with automatic calendar placement.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs px-3 py-1 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-subtle)] flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>AI powered</span>
            </span>
          </div>
        </div>
      </ScrollReveal>

      {/* Natural Language Input Card */}
      <ScrollReveal>
        <div className="apple-card p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <label
              htmlFor="goal-prompt-input"
              className="text-base font-semibold text-[var(--text-primary)] flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4 text-[var(--accent)]" />
              <span>What do you want to achieve?</span>
            </label>
            <span className="text-xs text-[var(--text-secondary)]">
              Specify goals, timeframes, or target dates
            </span>
          </div>

          <div className="relative">
            <textarea
              id="goal-prompt-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              disabled={decomposing}
              placeholder="e.g. Prepare for my DBMS exam in 10 days and finish my hackathon project"
              className="w-full px-4 py-3 text-base bg-[var(--fill-input)] border border-[var(--border-subtle)] rounded-xl text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent transition-all resize-none leading-relaxed"
            />
          </div>

          {/* Quick Example Chips */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs uppercase tracking-wider text-[var(--text-secondary)] font-medium mr-1">
              Examples:
            </span>
            <button
              type="button"
              onClick={() => {
                const text = "Prepare for my DBMS exam in 10 days and finish my hackathon project";
                setPrompt(text);
                handleDecompose(text);
              }}
              className="text-xs px-3 py-1 rounded-full bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-subtle)] transition-all cursor-pointer"
            >
              DBMS exam in 10 days & hackathon
            </button>
            <button
              type="button"
              onClick={() => {
                const text = "Launch NeuroFlow MVP in 5 days with demo video";
                setPrompt(text);
                handleDecompose(text);
              }}
              className="text-xs px-3 py-1 rounded-full bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-subtle)] transition-all cursor-pointer"
            >
              Launch MVP in 5 days
            </button>
            <button
              type="button"
              onClick={() => {
                const text = "Prepare for my DBMS exam";
                setPrompt(text);
                handleDecompose(text);
              }}
              className="text-xs px-3 py-1 rounded-full bg-[#ff9500]/10 hover:bg-[#ff9500]/20 text-[#c96500] dark:text-[#ff9f0a] border border-[#ff9500]/30 transition-all cursor-pointer"
              title="Tests inline clarifying questions"
            >
              Prepare exam (clarification test)
            </button>
          </div>

          {/* Action Button: Primary Pill Button */}
          <div className="flex items-center justify-end pt-2">
            <button
              id="decompose-btn"
              type="button"
              disabled={decomposing || !prompt.trim()}
              onClick={() => handleDecompose()}
              className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--accent)] hover:opacity-95 active:scale-[0.98] text-white font-medium text-xs shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {decomposing ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Decomposing goal...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Decompose goal</span>
                </>
              )}
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Inline Clarification Questions Box */}
      {clarificationNeeded && (
        <ScrollReveal>
          <div
            id="clarification-panel"
            className="apple-card p-6 border-l-4 border-l-[#ff9500] space-y-4"
          >
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-full bg-[#ff9500]/10 text-[#ff9500]">
                <HelpCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Clarification required: Scope or deadline missing
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  To build a realistic, non-conflicting schedule, please clarify the items below.
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-1">
              {clarifyingQuestions.map((question, qIdx) => (
                <div key={qIdx} className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-primary)] block">
                    {qIdx + 1}. {question}
                  </label>
                  <input
                    id={`clarify-input-${qIdx}`}
                    type="text"
                    placeholder="Type your answer here..."
                    value={clarificationAnswers[qIdx] || ""}
                    onChange={(e) =>
                      setClarificationAnswers((prev) => ({
                        ...prev,
                        [qIdx]: e.target.value,
                      }))
                    }
                    className="w-full px-3.5 py-2 text-xs bg-[var(--fill-input)] border border-[var(--border-subtle)] rounded-xl text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                  />
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2">
              <button
                id="submit-clarification-btn"
                type="button"
                onClick={handleClarificationSubmit}
                className="flex items-center gap-2 px-5 py-2 rounded-full bg-[var(--accent)] hover:opacity-95 text-white font-medium text-xs shadow-sm transition-all cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit answers & decompose</span>
              </button>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Loading Skeleton */}
      {decomposing && (
        <div id="decomposition-skeleton" className="space-y-4 animate-pulse">
          <div className="h-6 w-48 bg-[var(--bg-secondary)] rounded-lg" />
          <div className="apple-card p-6 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-[var(--border-subtle)]">
              <div className="h-5 w-64 bg-[var(--bg-secondary)] rounded-md" />
              <div className="h-5 w-32 bg-[var(--bg-secondary)] rounded-md" />
            </div>
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="grid grid-cols-12 gap-3 p-3 rounded-xl bg-[var(--bg-secondary)] items-center"
                >
                  <div className="col-span-1 h-4 bg-[var(--border-subtle)] rounded" />
                  <div className="col-span-4 h-4 bg-[var(--border-subtle)] rounded" />
                  <div className="col-span-2 h-4 bg-[var(--border-subtle)] rounded" />
                  <div className="col-span-2 h-4 bg-[var(--border-subtle)] rounded" />
                  <div className="col-span-2 h-4 bg-[var(--border-subtle)] rounded" />
                  <div className="col-span-1 h-4 bg-[var(--border-subtle)] rounded" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Success Notification */}
      {saveSuccess && (
        <ScrollReveal>
          <div
            id="save-success-banner"
            className="p-5 rounded-[22px] bg-emerald-500/10 border border-emerald-500/25 text-emerald-800 dark:text-emerald-300 space-y-2 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-[#34c759]" />
                <span className="text-sm font-semibold text-[var(--text-primary)]">
                  Workload successfully saved and scheduled
                </span>
              </div>
              <Link
                href="/"
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-[var(--accent)] text-white font-medium text-xs transition-all shadow-sm cursor-pointer"
              >
                <span>View timeline</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              {saveSuccess.saved_goals_count} goal(s) and {saveSuccess.saved_tasks_count} task(s) saved.
              {saveSuccess.scheduled_blocks_count !== undefined && (
                <span> {saveSuccess.scheduled_blocks_count} focus block(s) placed into your active schedule.</span>
              )}
            </p>
          </div>
        </ScrollReveal>
      )}

      {/* Editable Review Table */}
      {goals.length > 0 && !decomposing && (
        <ScrollReveal>
          <div id="editable-review-section" className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-[var(--text-primary)] tracking-tight flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[var(--accent)]" />
                  <span>Staged plan review</span>
                </h3>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  Review and edit task durations, importance, and deadlines before placing on the calendar.
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs text-[var(--text-secondary)] font-medium">
                  {totalTasks} tasks • {totalEstimatedHours}h total
                </span>
                <button
                  id="save-and-schedule-btn"
                  type="button"
                  disabled={savingAndScheduling || totalTasks === 0}
                  onClick={handleSaveAndSchedule}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--accent)] hover:opacity-95 text-white font-medium text-xs shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {savingAndScheduling ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Scheduling workload...</span>
                    </>
                  ) : (
                    <>
                      <Calendar className="w-3.5 h-3.5" />
                      <span>Save and schedule</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Goal Cards */}
            {goals.map((goal, gIdx) => (
              <div
                key={goal.id || gIdx}
                className="apple-card p-6 space-y-5"
              >
                {/* Goal Title & Target Date */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
                  <div className="flex-1 space-y-1">
                    <input
                      type="text"
                      value={goal.title}
                      onChange={(e) => updateGoalField(gIdx, "title", e.target.value)}
                      className="text-base font-semibold text-[var(--text-primary)] bg-transparent border-b border-transparent hover:border-[var(--border-subtle)] focus:border-[var(--accent)] focus:outline-none w-full transition-colors"
                      placeholder="Goal title"
                    />
                    <input
                      type="text"
                      value={goal.description}
                      onChange={(e) => updateGoalField(gIdx, "description", e.target.value)}
                      className="text-xs text-[var(--text-secondary)] bg-transparent border-b border-transparent hover:border-[var(--border-subtle)] focus:border-[var(--accent)] focus:outline-none w-full transition-colors"
                      placeholder="Goal description"
                    />
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-[var(--text-secondary)]">Target date:</span>
                    <input
                      type="date"
                      value={goal.target_date ? goal.target_date.slice(0, 10) : ""}
                      onChange={(e) => updateGoalField(gIdx, "target_date", e.target.value)}
                      className="px-2.5 py-1 text-xs bg-[var(--fill-input)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                    />
                    <button
                      type="button"
                      onClick={() => handleAddTask(gIdx)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] font-medium text-xs transition-all cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add task</span>
                    </button>
                  </div>
                </div>

                {/* Tasks Review Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] font-medium uppercase tracking-wider text-[10px]">
                        <th className="py-2.5 px-3 w-10">#</th>
                        <th className="py-2.5 px-3">Task title</th>
                        <th className="py-2.5 px-3 w-28">Minutes</th>
                        <th className="py-2.5 px-3 w-36">Importance</th>
                        <th className="py-2.5 px-3 w-36">Deadline</th>
                        <th className="py-2.5 px-3 w-28">Category</th>
                        <th className="py-2.5 px-3">AI rationale</th>
                        <th className="py-2.5 px-3 w-14 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {goal.tasks.map((task, tIdx) => (
                        <tr
                          key={task.id || tIdx}
                          className="hover:bg-[var(--bg-secondary)]/50 transition-colors group"
                        >
                          <td className="py-2.5 px-3 text-[var(--text-secondary)] text-[11px]">
                            {tIdx + 1}
                          </td>

                          <td className="py-2.5 px-3">
                            <input
                              id={`task-title-${gIdx}-${tIdx}`}
                              type="text"
                              value={task.title}
                              onChange={(e) =>
                                updateTaskField(gIdx, tIdx, "title", e.target.value)
                              }
                              className="w-full px-2 py-1 bg-transparent hover:bg-[var(--fill-input)] focus:bg-[var(--fill-input)] border border-transparent hover:border-[var(--border-subtle)] focus:border-[var(--accent)] rounded-lg text-[var(--text-primary)] font-medium focus:outline-none transition-all"
                            />
                          </td>

                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-1.5">
                              <input
                                id={`task-est-${gIdx}-${tIdx}`}
                                type="number"
                                min={15}
                                max={480}
                                step={15}
                                value={task.est_minutes}
                                onChange={(e) =>
                                  updateTaskField(
                                    gIdx,
                                    tIdx,
                                    "est_minutes",
                                    parseInt(e.target.value, 10) || 60
                                  )
                                }
                                className="w-16 px-2 py-1 bg-[var(--fill-input)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] text-center focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                              />
                              <span className="text-[11px] text-[var(--text-secondary)]">min</span>
                            </div>
                          </td>

                          <td className="py-2.5 px-3">
                            <select
                              id={`task-imp-${gIdx}-${tIdx}`}
                              value={task.importance}
                              onChange={(e) =>
                                updateTaskField(
                                  gIdx,
                                  tIdx,
                                  "importance",
                                  parseInt(e.target.value, 10)
                                )
                              }
                              className={`px-2.5 py-1 rounded-full text-xs font-medium border focus:outline-none ${
                                task.importance >= 5
                                  ? "pastel-pink"
                                  : task.importance === 4
                                  ? "pastel-orange"
                                  : "pastel-blue"
                              }`}
                            >
                              <option value={5}>5 - Urgent</option>
                              <option value={4}>4 - High</option>
                              <option value={3}>3 - Normal</option>
                              <option value={2}>2 - Moderate</option>
                              <option value={1}>1 - Low</option>
                            </select>
                          </td>

                          <td className="py-2.5 px-3">
                            <input
                              id={`task-deadline-${gIdx}-${tIdx}`}
                              type="date"
                              value={task.deadline ? task.deadline.slice(0, 10) : ""}
                              onChange={(e) =>
                                updateTaskField(gIdx, tIdx, "deadline", e.target.value)
                              }
                              className="px-2 py-1 text-xs bg-[var(--fill-input)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                            />
                          </td>

                          <td className="py-2.5 px-3">
                            <input
                              id={`task-category-${gIdx}-${tIdx}`}
                              type="text"
                              value={task.category || "general"}
                              onChange={(e) =>
                                updateTaskField(gIdx, tIdx, "category", e.target.value)
                              }
                              className="w-20 px-2 py-0.5 text-xs font-medium uppercase bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-md text-[var(--text-secondary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                            />
                          </td>

                          <td className="py-2.5 px-3 text-xs text-[var(--text-secondary)] max-w-xs truncate" title={task.rationale}>
                            {task.rationale || "Core step for goal achievement"}
                          </td>

                          <td className="py-2.5 px-3 text-center">
                            <button
                              id={`task-delete-${gIdx}-${tIdx}`}
                              type="button"
                              onClick={() => handleDeleteTask(gIdx, tIdx)}
                              className="p-1 rounded-full text-[var(--text-secondary)] hover:text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer"
                              title="Delete task"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </ScrollReveal>
      )}
    </div>
  );
}
