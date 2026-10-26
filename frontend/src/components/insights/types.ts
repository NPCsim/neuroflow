export interface RecommendationItem {
  id: string;
  title: string;
  description: string;
  category: string;
  impact: "high" | "medium" | "low" | string;
  supporting_metric: string;
  action_type?: string | null;
  actionable_step?: string | null;
}

export interface ActivityStats {
  total_logs_analyzed: number;
  overall_completion_rate: number;
  overall_completion_rate_pct: number;
  total_completed: number;
  total_missed: number;
  completion_rate_by_category?: Record<
    string,
    {
      completed: number;
      missed: number;
      total: number;
      completion_rate: number;
      completion_rate_pct: number;
    }
  >;
  completion_rate_by_time_of_day?: Record<
    string,
    {
      completed: number;
      missed: number;
      total: number;
      completion_rate: number;
      completion_rate_pct: number;
    }
  >;
  planned_vs_actual_duration?: {
    overall_ratio: number;
    total_planned_minutes: number;
    total_actual_minutes: number;
    trend: string;
    by_category?: Record<string, number>;
  };
  most_missed_task_types?: Array<{
    category: string;
    missed_count: number;
    total_count: number;
    missed_rate_pct: number;
  }>;
  overload_days?: Array<{
    date: string;
    missed_blocks_count: number;
    total_blocks_count: number;
    status: string;
    reason: string;
  }>;
}

export interface InsightsResponse {
  date: string;
  generated_at: string;
  is_cached: boolean;
  stats: ActivityStats;
  recommendations: RecommendationItem[];
}

export interface CompletionTrendPoint {
  date: string;
  day: string;
  rate: number;
  completed: number;
  missed: number;
}

export interface PlannedVsActualPoint {
  category: string;
  plannedHours: number;
  actualHours: number;
  varianceHours: number;
}

export interface CategoryFocusPoint {
  name: string;
  hours: number;
  percentage: number;
  color: string;
}

export interface HeatmapDay {
  date: string;
  dayOfWeek: string;
  dayIndex: number; // 0=Mon, 6=Sun
  weekIndex: number;
  loadPct: number;
  scheduledHours: number;
  capacityHours: number;
  isOverloaded: boolean;
  isToday: boolean;
}
