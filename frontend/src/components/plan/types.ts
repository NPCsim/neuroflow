export interface ScheduleBlockItem {
  id: string;
  task_id: string | null;
  title: string;
  start_time: string;
  end_time: string;
  chunk_index: number;
  total_chunks: number;
  is_completed: boolean;
  is_at_risk: boolean;
  status: "planned" | "completed" | "missed";
  is_stuck?: boolean;
  goal_id?: string | null;
  goal_title?: string | null;
  goal_color?: string | null;
  priority?: string | null;
  deadline?: string | null;
}

export interface FixedEventItem {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  source: string;
}

export interface GoalSummary {
  id: string;
  title: string;
  description?: string | null;
  color: string;
}

export interface RemedyOption {
  action: string;
  task_id?: string | null;
  title: string;
  description: string;
  parameters: Record<string, any>;
  impact_hours: number;
  impact_description: string;
}

export interface WorkloadProblem {
  id: string;
  task_id?: string | null;
  problem_type: string;
  description: string;
  severity: "critical" | "warning" | "info";
  hours_needed?: number | null;
  hours_available?: number | null;
  remedies: RemedyOption[];
}

export interface DayLoad {
  date: string;
  day_of_week: string;
  scheduled_minutes: number;
  capacity_minutes: number;
  fixed_event_minutes: number;
  total_committed_minutes: number;
  load_percentage: number;
  is_overloaded: boolean;
}

export interface WorkloadAnalysis {
  realism_score: number;
  status: "realistic" | "tight" | "overloaded" | "critical" | string;
  daily_loads: DayLoad[];
  problems: WorkloadProblem[];
  total_scheduled_hours: number;
  total_capacity_hours: number;
  total_fixed_event_hours: number;
}

export interface ScheduleOverviewData {
  status: string;
  current_time: string;
  blocks: ScheduleBlockItem[];
  fixed_events: FixedEventItem[];
  goals: GoalSummary[];
  workload: WorkloadAnalysis;
  today?: DayLoad | null;
}

export interface PlanDiffMoved {
  task_id: string;
  title: string;
  old_start?: string | null;
  new_start: string;
  old_end?: string | null;
  new_end: string;
  diff_minutes?: number | null;
  from_start?: string | null;
  to_start?: string | null;
  reason?: string | null;
}

export interface PlanDiffDeferred {
  task_id: string;
  title: string;
  old_deadline?: string | null;
  new_deadline?: string | null;
  reason: string;
}

export interface PlanDiffDropped {
  task_id: string;
  title: string;
  remaining_minutes?: number;
  reason: string;
}

export interface PlanDiffAtRisk {
  task_id: string;
  title: string;
  deadline?: string | null;
  scheduled_end?: string | null;
  reason: string;
}

export interface PlanDiffPayload {
  moved?: PlanDiffMoved[];
  deferred?: PlanDiffDeferred[];
  dropped?: PlanDiffDropped[];
  at_risk?: PlanDiffAtRisk[];
  "at-risk"?: PlanDiffAtRisk[];
}

export interface AgentCommandResponseData {
  summary: string;
  diff: PlanDiffPayload;
  snapshot_id: string;
  proposal_id?: string;
  status: string;
  steps_executed?: number;
}

