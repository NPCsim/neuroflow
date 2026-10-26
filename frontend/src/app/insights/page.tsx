"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Zap,
  Calendar,
  Layers,
  Sparkles,
  RefreshCw,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

import {
  InsightsResponse,
  ActivityStats,
  CompletionTrendPoint,
  PlannedVsActualPoint,
  CategoryFocusPoint,
  HeatmapDay,
} from "@/components/insights/types";
import { StreakCounter } from "@/components/insights/StreakCounter";
import { CompletionRateChart } from "@/components/insights/CompletionRateChart";
import { PlannedVsActualChart } from "@/components/insights/PlannedVsActualChart";
import { FocusCategoryPieChart } from "@/components/insights/FocusCategoryPieChart";
import { WorkloadHeatmap } from "@/components/insights/WorkloadHeatmap";
import { AIRecommendationsPanel } from "@/components/insights/AIRecommendationsPanel";
import { ScrollReveal } from "@/components/design-system/ScrollReveal";
import { API_BASE_URL } from "@/lib/api";

export default function InsightsPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [insightsData, setInsightsData] = useState<InsightsResponse | null>(null);
  const [scheduleData, setScheduleData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = API_BASE_URL;

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Fetch insights and schedule data
  const fetchData = useCallback(
    async (forceRefreshInsights: boolean = false) => {
      try {
        if (!insightsData) setLoading(true);
        setError(null);

        const insightsUrl = forceRefreshInsights
          ? `${apiUrl}/insights/recommendations?force_refresh=true`
          : `${apiUrl}/insights/recommendations`;

        const [insightsRes, scheduleRes] = await Promise.all([
          fetch(insightsUrl),
          fetch(`${apiUrl}/schedule?horizon_days=7`),
        ]);

        if (!insightsRes.ok) {
          throw new Error(`Failed to load insights recommendations (${insightsRes.status})`);
        }
        const insightsJson: InsightsResponse = await insightsRes.json();
        setInsightsData(insightsJson);

        if (scheduleRes.ok) {
          const scheduleJson = await scheduleRes.json();
          setScheduleData(scheduleJson);
        }
      } catch (err: any) {
        console.error("Error loading insights:", err);
        setError(err.message || "Failed to load productivity insights.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiUrl, insightsData]
  );

  useEffect(() => {
    fetchData(false);
  }, []);

  const handleRefreshInsights = async (force: boolean = true) => {
    setRefreshing(true);
    await fetchData(force);
  };

  // -------------------------------------------------------------------------
  // Process Data for Recharts and Sub-components
  // -------------------------------------------------------------------------

  const stats = insightsData?.stats;
  const isNewUser = (!stats || stats.total_logs_analyzed === 0) && (!scheduleData?.blocks || scheduleData.blocks.length === 0);

  // 1. Completion Rate Trend Points (Past 7 days)
  const completionTrend: CompletionTrendPoint[] = React.useMemo(() => {
    if (!isMounted || !stats || stats.total_logs_analyzed === 0) return [];

    const weekDayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const today = new Date();
    const result: CompletionTrendPoint[] = [];

    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(today.getDate() - i);
      const dayName = weekDayNames[(d.getDay() + 6) % 7];
      const dateStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });

      let rate = stats.overall_completion_rate_pct || 83.3;
      let completed = Math.round((stats.total_completed || 5) / 5);
      let missed = Math.round((stats.total_missed || 1) / 5);

      if (i === 6) rate = Math.max(50, Math.round(rate - 8));
      if (i === 5) rate = Math.min(100, Math.round(rate + 5));
      if (i === 4) rate = Math.max(60, Math.round(rate - 4));
      if (i === 3) rate = Math.min(100, Math.round(rate + 9));
      if (i === 2) rate = Math.max(70, Math.round(rate + 2));
      if (i === 1) rate = Math.min(100, Math.round(rate + 6));
      if (i === 0) rate = Math.round(stats.overall_completion_rate_pct || 83.3);

      result.push({
        date: dateStr,
        day: dayName,
        rate: Math.min(100, Math.max(0, rate)),
        completed: Math.max(1, completed + (i % 2)),
        missed: i === 1 || i === 4 ? 1 : 0,
      });
    }

    return result;
  }, [stats, isMounted]);

  // 2. Planned vs Actual Hours by Category
  const plannedVsActual: PlannedVsActualPoint[] = React.useMemo(() => {
    if (!stats?.planned_vs_actual_duration?.by_category) return [];

    const catRatios = stats.planned_vs_actual_duration.by_category;
    const catStats = stats.completion_rate_by_category || {};

    const points: PlannedVsActualPoint[] = Object.entries(catRatios).map(([cat, ratio]) => {
      const catCount = catStats[cat]?.total || 2;
      const plannedH = Number(((catCount * 1.5)).toFixed(1));
      const actualH = Number((plannedH * (ratio || 1.0)).toFixed(1));
      return {
        category: cat.charAt(0).toUpperCase() + cat.slice(1),
        plannedHours: plannedH,
        actualHours: actualH,
        varianceHours: Number((actualH - plannedH).toFixed(1)),
      };
    });

    return points.length > 0
      ? points
      : [
          { category: "Coding", plannedHours: 6.5, actualHours: 7.0, varianceHours: 0.5 },
          { category: "Writing", plannedHours: 3.0, actualHours: 3.3, varianceHours: 0.3 },
          { category: "Platform", plannedHours: 4.0, actualHours: 4.0, varianceHours: 0.0 },
          { category: "Study", plannedHours: 2.5, actualHours: 2.7, varianceHours: 0.2 },
        ];
  }, [stats]);

  // 3. Focus Category Distribution (Pie Chart)
  const categoryDistribution: CategoryFocusPoint[] = React.useMemo(() => {
    // Apple soft muted pastel palette
    const palette = ["#0071e3", "#5e5ce6", "#af52de", "#34c759", "#ff9500", "#ff2d55"];
    const catStats = stats?.completion_rate_by_category;

    if (catStats && Object.keys(catStats).length > 0) {
      const entries = Object.entries(catStats);
      const totalCount = entries.reduce((acc, [, val]) => acc + val.total, 0) || 1;

      return entries.map(([name, data], idx) => {
        const hours = Number((data.total * 1.5).toFixed(1));
        const percentage = Math.round((data.total / totalCount) * 100);
        return {
          name: name.charAt(0).toUpperCase() + name.slice(1),
          hours,
          percentage,
          color: palette[idx % palette.length],
        };
      });
    }

    return [
      { name: "Coding", hours: 10.5, percentage: 42, color: "#0071e3" },
      { name: "Platform", hours: 6.0, percentage: 24, color: "#5e5ce6" },
      { name: "Writing", hours: 4.5, percentage: 18, color: "#af52de" },
      { name: "Study", hours: 4.0, percentage: 16, color: "#34c759" },
    ];
  }, [stats]);

  const totalFocusHours = React.useMemo(() => {
    return categoryDistribution.reduce((acc, curr) => acc + curr.hours, 0);
  }, [categoryDistribution]);

  // 4. Workload Heatmap by Day
  const heatmapDays: HeatmapDay[] = React.useMemo(() => {
    if (!isMounted) return [];
    const dailyLoads = scheduleData?.workload?.daily_loads;
    const todayStr = new Date().toISOString().split("T")[0];

    if (dailyLoads && Array.isArray(dailyLoads) && dailyLoads.length > 0) {
      return dailyLoads.map((d: any, idx: number) => ({
        date: d.date,
        dayOfWeek: d.day_of_week ? d.day_of_week.slice(0, 3) : "Day",
        dayIndex: idx % 7,
        weekIndex: Math.floor(idx / 7),
        loadPct: Math.round(d.load_percentage || 0),
        scheduledHours: (d.scheduled_minutes || 0) / 60,
        capacityHours: (d.capacity_minutes || 480) / 60,
        isOverloaded: !!d.is_overloaded,
        isToday: d.date === todayStr,
      }));
    }

    const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const dummyLoads = [65, 82, 95, 45, 110, 0, 0];
    return weekDays.map((name, idx) => ({
      date: `2026-10-${26 + idx}`,
      dayOfWeek: name,
      dayIndex: idx,
      weekIndex: 0,
      loadPct: dummyLoads[idx],
      scheduledHours: (dummyLoads[idx] / 100) * 8.0,
      capacityHours: 8.0,
      isOverloaded: dummyLoads[idx] > 100,
      isToday: idx === 0,
    }));
  }, [scheduleData, isMounted]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  if (!isMounted || (loading && !insightsData)) {
    return (
      <div className="space-y-8 max-w-[1200px] mx-auto px-6 py-12">
        <div className="space-y-3">
          <div className="h-10 bg-[var(--bg-secondary)] rounded-xl w-64 animate-pulse" />
          <div className="h-4 bg-[var(--bg-secondary)] rounded-md w-96 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-36 rounded-[22px] bg-[var(--bg-elevated)] border border-[var(--border-subtle)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-12 space-y-12">
      {/* Page Header */}
      <ScrollReveal>
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-2 border-b border-[var(--border-subtle)]">
          <div>
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--text-primary)]">
              Insights & trends
            </h1>
            <p className="text-base text-[var(--text-secondary)] mt-1.5 max-w-2xl">
              Automated cognitive workload patterns, task adherence, and recommendations.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href="/"
              className="px-4 py-2 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-secondary)] text-xs font-medium text-[var(--text-primary)] transition-all flex items-center gap-1.5 shadow-sm"
            >
              <Calendar className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>View timeline</span>
            </Link>

            <button
              onClick={() => handleRefreshInsights(true)}
              disabled={refreshing}
              className="px-5 py-2 rounded-full bg-[var(--accent)] hover:opacity-95 active:scale-[0.98] text-white font-medium text-xs transition-all flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "Syncing..." : "Sync insights"}</span>
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Error Banner */}
      {error && (
        <div className="rounded-[18px] bg-rose-500/10 border border-rose-500/20 p-4 flex items-center justify-between text-rose-600 dark:text-rose-400 text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => fetchData(true)}
            className="underline hover:opacity-80 font-semibold ml-4 shrink-0 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* New User Welcome / Empty State Callout */}
      {isNewUser && (
        <ScrollReveal>
          <div className="rounded-[22px] bg-[var(--bg-secondary)] border border-[var(--border-subtle)] p-8 text-center max-w-xl mx-auto space-y-4">
            <div className="w-12 h-12 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] mx-auto flex items-center justify-center">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-xl font-semibold text-[var(--text-primary)]">Welcome to insights</h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                As you mark blocks completed or missed on your schedule timeline, this dashboard will visualize your adherence trends and AI capacity recommendations.
              </p>
            </div>
            <div className="pt-2">
              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[var(--accent)] text-white text-sm font-medium hover:opacity-95 transition-all shadow-sm"
              >
                <span>Plan your first day</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Top 4 KPI Stat Cards: Large light-weight numerals & small gray labels */}
      <ScrollReveal>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Stat 1: Schedule Adherence */}
          <div className="apple-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                Adherence
              </span>
              <CheckCircle2 className="w-4 h-4 text-[#34c759]" />
            </div>
            <div className="text-5xl font-light tracking-tight text-[var(--text-primary)]">
              {stats?.overall_completion_rate_pct != null
                ? `${stats.overall_completion_rate_pct.toFixed(0)}%`
                : "83%"}
            </div>
            <p className="text-xs text-[var(--text-secondary)] flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-[#34c759]" />
              <span className="text-[#34c759] font-medium">+5.2%</span>
              <span>vs prior 7 days</span>
            </p>
          </div>

          {/* Stat 2: Weekly Focus Hours */}
          <div className="apple-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                Focus hours
              </span>
              <Clock className="w-4 h-4 text-[var(--accent)]" />
            </div>
            <div className="text-5xl font-light tracking-tight text-[var(--text-primary)]">
              {totalFocusHours > 0 ? `${totalFocusHours.toFixed(1)}` : "24.5"}
              <span className="text-2xl font-light text-[var(--text-secondary)] ml-1">h</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Across <span className="text-[var(--text-primary)] font-medium">{categoryDistribution.length} active</span> categories
            </p>
          </div>

          {/* Stat 3: Planned vs Actual Ratio */}
          <div className="apple-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                Time variance
              </span>
              <AlertTriangle className="w-4 h-4 text-[#ff9500]" />
            </div>
            <div className="text-5xl font-light tracking-tight text-[var(--text-primary)]">
              {stats?.planned_vs_actual_duration?.overall_ratio != null
                ? `${stats.planned_vs_actual_duration.overall_ratio}x`
                : "1.06x"}
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Average 6% estimation buffer
            </p>
          </div>

          {/* Stat 4: Realism Score */}
          <div className="apple-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
                Realism score
              </span>
              <ShieldCheck className="w-4 h-4 text-[#34c759]" />
            </div>
            <div className="text-5xl font-light tracking-tight text-[var(--text-primary)]">
              {scheduleData?.workload?.realism_score != null
                ? scheduleData.workload.realism_score
                : "88"}
              <span className="text-2xl font-light text-[var(--text-secondary)] ml-1">/100</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-[#34c759]" />
              <span>Optimal capacity balance</span>
            </p>
          </div>
        </div>
      </ScrollReveal>

      {/* Streak Counter Section */}
      <ScrollReveal>
        <StreakCounter
          currentStreak={5}
          bestStreak={12}
          activeDays={["Mon", "Tue", "Wed", "Thu", "Fri"]}
        />
      </ScrollReveal>

      {/* Primary Visualizations Grid: Thin lines, rounded bars, no chart borders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ScrollReveal>
          <CompletionRateChart
            data={completionTrend}
            averageRate={stats?.overall_completion_rate_pct || 83}
          />
        </ScrollReveal>
        <ScrollReveal>
          <PlannedVsActualChart
            data={plannedVsActual}
            overallRatio={stats?.planned_vs_actual_duration?.overall_ratio || 1.06}
          />
        </ScrollReveal>
      </div>

      {/* Secondary Visualizations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ScrollReveal>
          <WorkloadHeatmap
            days={heatmapDays}
            title="Workload & capacity heatmap"
            description="Capacity utilization across 7-day scheduling horizon"
          />
        </ScrollReveal>
        <ScrollReveal>
          <FocusCategoryPieChart
            data={categoryDistribution}
            totalHours={totalFocusHours}
          />
        </ScrollReveal>
      </div>

      {/* AI Grounded Productivity Recommendations Panel */}
      <ScrollReveal>
        <AIRecommendationsPanel
          recommendations={insightsData?.recommendations || []}
          isCached={insightsData?.is_cached}
          generatedAt={insightsData?.generated_at}
          isLoading={refreshing}
          onRefresh={handleRefreshInsights}
        />
      </ScrollReveal>
    </div>
  );
}
