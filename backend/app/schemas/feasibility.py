from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RemedyOptionResponse(BaseModel):
    action: str = Field(..., description="Action name, e.g. extend_deadline, reduce_scope, defer_task, drop_task, add_time_block")
    task_id: Optional[str] = Field(None, description="Task ID this remedy applies to")
    title: str = Field(..., description="Short remedy title")
    description: str = Field(..., description="Human-readable remedy description")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Machine-readable action parameters")
    impact_hours: float = Field(..., description="Hours saved or gained by applying this remedy")
    impact_description: str = Field(..., description="Description of the quantitative impact")


class WorkloadProblemResponse(BaseModel):
    id: str = Field(..., description="Unique problem identifier")
    task_id: Optional[str] = Field(None, description="Related task ID if applicable")
    problem_type: str = Field(..., description="Type: deadline_deficit, daily_overload, at_risk_overflow")
    description: str = Field(..., description="Clear diagnostic explanation")
    severity: str = Field(..., description="critical, warning, or info")
    hours_needed: Optional[float] = None
    hours_available: Optional[float] = None
    remedies: List[RemedyOptionResponse] = Field(default_factory=list, description="Machine-readable remedy options")


class DayLoadResponse(BaseModel):
    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    day_of_week: str = Field(..., description="Day name, e.g. Monday")
    scheduled_minutes: int
    capacity_minutes: int
    fixed_event_minutes: int
    total_committed_minutes: int
    load_percentage: float = Field(..., description="Load percentage against available working capacity")
    is_overloaded: bool = Field(..., description="True if load exceeds 100%")


class WorkloadAnalysisResponse(BaseModel):
    realism_score: int = Field(..., ge=0, le=100, description="Overall realism score from 0 (impossible) to 100 (optimal)")
    status: str = Field(..., description="realistic, tight, overloaded, or critical")
    daily_loads: List[DayLoadResponse]
    problems: List[WorkloadProblemResponse]
    total_scheduled_hours: float
    total_capacity_hours: float
    total_fixed_event_hours: float


class ScheduleBlockItemResponse(BaseModel):
    id: str
    task_id: Optional[str] = None
    title: str
    start_time: datetime
    end_time: datetime
    chunk_index: int = 1
    total_chunks: int = 1
    is_completed: bool = False
    is_at_risk: bool = False
    status: str = "planned"
    is_stuck: bool = False
    goal_id: Optional[str] = None
    goal_title: Optional[str] = None
    goal_color: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None


class FixedEventItemResponse(BaseModel):
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    source: str = "manual"


class GoalSummaryResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    color: str = "indigo"


class ScheduleBlockStatusRequest(BaseModel):
    status: str = Field(..., description="completed, missed, or planned")


class ScheduleRescheduleRequest(BaseModel):
    block_id: str
    new_start: datetime
    new_end: Optional[datetime] = None


class ApplyRemedyRequest(BaseModel):
    action: str
    task_id: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScheduleOverviewResponse(BaseModel):
    status: str = "success"
    current_time: datetime
    blocks: List[ScheduleBlockItemResponse]
    fixed_events: List[FixedEventItemResponse]
    goals: List[GoalSummaryResponse]
    workload: WorkloadAnalysisResponse
    today: Optional[DayLoadResponse] = None


class UnscheduledTaskItemResponse(BaseModel):
    task_id: str
    title: str
    reason: str
    at_risk: bool = False
    scheduled_minutes: int = 0
    remaining_minutes: int = 0
    deadline: Optional[datetime] = None
    is_stuck: bool = False
    flag: Optional[str] = None
    carry_over_count: int = 0


class ScheduleRebuildRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30, description="Horizon in days to schedule")
    start: Optional[datetime] = Field(default=None, description="Start time for scheduling, defaults to now UTC")


class ScheduleRebuildResponse(BaseModel):
    status: str = "success"
    message: str
    scheduled_blocks_count: int
    unscheduled_tasks_count: int
    blocks: List[ScheduleBlockItemResponse]
    unscheduled_tasks: List[UnscheduledTaskItemResponse]
    workload_analysis: WorkloadAnalysisResponse


class StuckTaskResponse(BaseModel):
    id: str
    title: str
    carry_over_count: int
    status: str
    is_stuck: bool = True
    flag: str = "stuck"
    remaining_duration_minutes: Optional[int] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None


class RolloverTaskResponse(BaseModel):
    id: str
    title: str
    carry_over_count: int = 0
    status: str
    is_stuck: bool = False
    flag: Optional[str] = None
    remaining_duration_minutes: Optional[int] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None


class ActivityLogItemResponse(BaseModel):
    id: str
    task_id: Optional[str] = None
    schedule_block_id: Optional[str] = None
    action: str
    title: Optional[str] = None
    description: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime


class ScheduleRolloverRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30, description="Horizon in days to schedule")
    now: Optional[datetime] = Field(default=None, description="Explicit reference time for rollover, defaults to now UTC")
    current_time: Optional[datetime] = Field(default=None, description="Alias for now")
    start: Optional[datetime] = Field(default=None, description="Alias for now")


class ScheduleRolloverResponse(BaseModel):
    status: str = "success"
    message: str
    rollover_time: datetime
    missed_blocks_count: int
    carried_over_tasks_count: int
    stuck_tasks_count: int
    stuck_tasks: List[StuckTaskResponse] = Field(default_factory=list, description="Tasks carried over 3+ times, flagged as stuck")
    stuck_task_ids: List[str] = Field(default_factory=list, description="List of stuck task IDs")
    carried_over_tasks: List[RolloverTaskResponse] = Field(default_factory=list, description="Tasks whose carry-over counts were incremented")
    tasks: List[RolloverTaskResponse] = Field(default_factory=list, description="All active tasks after rollover with carry-over counts and stuck flags")
    missed_blocks: List[ScheduleBlockItemResponse] = Field(default_factory=list, description="Past blocks marked as missed")
    blocks: List[ScheduleBlockItemResponse] = Field(default_factory=list, description="Active schedule blocks placed by build_schedule")
    scheduled_blocks: List[ScheduleBlockItemResponse] = Field(default_factory=list, description="Alias for blocks")
    scheduled_blocks_count: int = 0
    unscheduled_tasks: List[UnscheduledTaskItemResponse] = Field(default_factory=list)
    unscheduled_tasks_count: int = 0
    activity_logs: List[ActivityLogItemResponse] = Field(default_factory=list, description="Activity logs generated during rollover")
    workload_analysis: Optional[WorkloadAnalysisResponse] = None
