from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from scheduler import (
    TaskInput,
    FixedEventInput,
    ScheduleSettingsInput,
    ScheduledBlock,
    _ensure_utc,
    _parse_time_str,
    _to_task_input,
    _to_fixed_event_input,
    _to_settings_input,
    _generate_free_intervals,
)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RemedyOption:
    action: str  # "extend_deadline", "reduce_scope", "defer_task", "drop_task", "add_time_block"
    task_id: str | None
    title: str
    description: str
    parameters: dict[str, Any]
    impact_hours: float
    impact_description: str


@dataclass
class WorkloadProblem:
    id: str
    task_id: str | None
    problem_type: str  # "deadline_deficit", "daily_overload", "at_risk_overflow", "unresolvable_dependency"
    description: str
    severity: str  # "critical", "warning", "info"
    hours_needed: float | None = None
    hours_available: float | None = None
    remedies: list[RemedyOption] = field(default_factory=list)


@dataclass
class DayLoadInfo:
    date: str  # YYYY-MM-DD
    day_of_week: str  # Monday, Tuesday...
    scheduled_minutes: int
    capacity_minutes: int
    fixed_event_minutes: int
    total_committed_minutes: int
    load_percentage: float
    is_overloaded: bool


@dataclass
class WorkloadAnalysisResult:
    realism_score: int  # 0 to 100
    status: str  # "realistic", "tight", "overloaded", "critical"
    daily_loads: list[DayLoadInfo]
    problems: list[WorkloadProblem]
    total_scheduled_hours: float
    total_capacity_hours: float
    total_fixed_event_hours: float


# ---------------------------------------------------------------------------
# Internal Normalization Helpers
# ---------------------------------------------------------------------------

def _to_scheduled_block(item: Any) -> ScheduledBlock:
    if isinstance(item, ScheduledBlock):
        return item
    if isinstance(item, dict):
        return ScheduledBlock(
            id=str(item.get("id", uuid.uuid4())),
            task_id=str(item.get("task_id", "")),
            title=item.get("title", ""),
            start_time=_ensure_utc(item["start_time"]),
            end_time=_ensure_utc(item["end_time"]),
            chunk_index=int(item.get("chunk_index", 1)),
            total_chunks=int(item.get("total_chunks", 1)),
            is_completed=bool(item.get("is_completed", False)),
            is_at_risk=bool(item.get("is_at_risk", False)),
        )
    return ScheduledBlock(
        id=str(getattr(item, "id", uuid.uuid4())),
        task_id=str(getattr(item, "task_id", "")),
        title=getattr(item, "title", ""),
        start_time=_ensure_utc(getattr(item, "start_time")),
        end_time=_ensure_utc(getattr(item, "end_time")),
        chunk_index=int(getattr(item, "chunk_index", 1)),
        total_chunks=int(getattr(item, "total_chunks", 1)),
        is_completed=bool(getattr(item, "is_completed", False)),
        is_at_risk=bool(getattr(item, "is_at_risk", False)),
    )


# ---------------------------------------------------------------------------
# Core Analysis Engine
# ---------------------------------------------------------------------------

def analyze_workload(
    tasks: Sequence[TaskInput | dict | Any],
    schedule: Sequence[ScheduledBlock | dict | Any],
    settings: ScheduleSettingsInput | dict | Any = None,
    fixed_events: Sequence[FixedEventInput | dict | Any] = (),
    now: datetime | None = None,
    horizon_days: int = 7,
) -> WorkloadAnalysisResult:
    """
    Analyzes workload realism, detects capacity overloads and deadline deficits,
    computes an overall realism score (0-100), and generates 2-3 machine-readable
    remedy options with calculated quantitative impact for each detected problem.
    """
    settings_obj = _to_settings_input(settings or ScheduleSettingsInput())
    now_utc = _ensure_utc(now or datetime.now(timezone.utc))

    try:
        user_tz = ZoneInfo(settings_obj.timezone_str)
    except Exception:
        user_tz = timezone.utc

    now_user = now_utc.astimezone(user_tz)
    all_tasks = [_to_task_input(t) for t in tasks]
    all_blocks = [_to_scheduled_block(b) for b in schedule]
    all_fixed = [_to_fixed_event_input(e) for e in fixed_events]

    work_start_t = _parse_time_str(settings_obj.work_start_time)
    work_end_t = _parse_time_str(settings_obj.work_end_time)
    standard_day_capacity = int(
        (datetime.combine(date.today(), work_end_t) - datetime.combine(date.today(), work_start_t)).total_seconds() // 60
    )

    # 1. Per-Day Load Calculation
    daily_loads: list[DayLoadInfo] = []
    daily_overloaded_days: list[DayLoadInfo] = []
    tight_days: list[DayLoadInfo] = []

    current_date = now_user.date()
    date_blocks_map: dict[str, list[ScheduledBlock]] = {}

    for day_offset in range(horizon_days):
        day = current_date + timedelta(days=day_offset)
        date_str = day.isoformat()
        is_work_day = day.weekday() in settings_obj.work_days

        # Capacity for this day in minutes
        day_capacity = standard_day_capacity if is_work_day else 0

        # Blocks falling on this day in user timezone
        day_blocks: list[ScheduledBlock] = []
        sched_mins = 0
        for b in all_blocks:
            b_local_start = b.start_time.astimezone(user_tz)
            if b_local_start.date() == day:
                day_blocks.append(b)
                sched_mins += int((b.end_time - b.start_time).total_seconds() // 60)

        date_blocks_map[date_str] = day_blocks

        # Fixed events on this day
        fe_mins = 0
        for fe in all_fixed:
            fe_local_start = fe.start_time.astimezone(user_tz)
            if fe_local_start.date() == day:
                fe_mins += int((fe.end_time - fe.start_time).total_seconds() // 60)

        total_committed = sched_mins + fe_mins
        load_pct = (
            round((total_committed / day_capacity) * 100.0, 1)
            if day_capacity > 0
            else (100.0 if total_committed > 0 else 0.0)
        )
        is_over = load_pct > 100.0

        load_info = DayLoadInfo(
            date=date_str,
            day_of_week=day.strftime("%A"),
            scheduled_minutes=sched_mins,
            capacity_minutes=day_capacity,
            fixed_event_minutes=fe_mins,
            total_committed_minutes=total_committed,
            load_percentage=load_pct,
            is_overloaded=is_over,
        )
        daily_loads.append(load_info)

        if is_over:
            daily_overloaded_days.append(load_info)
        elif load_pct >= 85.0:
            tight_days.append(load_info)

    # 2. Problem Detection & Remedy Generation
    problems: list[WorkloadProblem] = []

    # Problem Category A: Deadline Deficits (Task needs X hours but only Y free hours before deadline)
    # Generate available free intervals across horizon
    free_intervals = _generate_free_intervals(
        settings=settings_obj,
        fixed_events=all_fixed,
        start=now_utc,
        horizon_days=horizon_days,
    )

    for task in all_tasks:
        if task.is_completed:
            continue

        rem_min = task.get_remaining_minutes()
        if rem_min <= 0:
            continue

        if task.deadline is not None:
            deadline_utc = _ensure_utc(task.deadline)
            deadline_user = deadline_utc.astimezone(user_tz)
            deadline_str = deadline_user.strftime("%A at %I:%M %p")

            # Calculate free minutes available between now and deadline
            free_mins_before_deadline = 0
            for inv in free_intervals:
                if inv.start_time >= deadline_utc:
                    break
                inv_effective_end = min(inv.end_time, deadline_utc)
                if inv_effective_end > inv.start_time:
                    free_mins_before_deadline += int((inv_effective_end - inv.start_time).total_seconds() // 60)

            if rem_min > free_mins_before_deadline:
                deficit_minutes = rem_min - free_mins_before_deadline
                needed_h = round(rem_min / 60.0, 1)
                avail_h = round(free_mins_before_deadline / 60.0, 1)
                deficit_h = round(deficit_minutes / 60.0, 1)

                problem_id = f"prob_deficit_{task.id}"
                desc = (
                    f"Task '{task.title}' due {deadline_str} needs {needed_h}h "
                    f"but only {avail_h}h free before then"
                )

                # Generate 3 machine-readable remedy options
                # Remedy 1: Extend Deadline
                # Calculate new deadline that captures required deficit
                extra_needed = deficit_minutes
                extended_deadline = deadline_user
                for d_off in range(1, 10):
                    cand_day = deadline_user.date() + timedelta(days=d_off)
                    if cand_day.weekday() in settings_obj.work_days:
                        extra_needed -= standard_day_capacity
                        extended_deadline = datetime.combine(cand_day, work_end_t, tzinfo=user_tz)
                        if extra_needed <= 0:
                            break

                remedy_extend = RemedyOption(
                    action="extend_deadline",
                    task_id=task.id,
                    title="Extend task deadline",
                    description=f"Move deadline to {extended_deadline.strftime('%A, %b %d at %I:%M %p')}",
                    parameters={
                        "task_id": task.id,
                        "suggested_deadline": extended_deadline.astimezone(timezone.utc).isoformat(),
                    },
                    impact_hours=deficit_h,
                    impact_description=f"Gains {deficit_h}h required capacity before new deadline",
                )

                # Remedy 2: Reduce Scope
                reduced_duration = max(free_mins_before_deadline, 30)
                saved_h = round((rem_min - reduced_duration) / 60.0, 1)
                remedy_reduce = RemedyOption(
                    action="reduce_scope",
                    task_id=task.id,
                    title="Reduce task scope",
                    description=f"Trim estimated duration to {reduced_duration} mins to fit available window",
                    parameters={
                        "task_id": task.id,
                        "suggested_duration_minutes": reduced_duration,
                    },
                    impact_hours=saved_h,
                    impact_description=f"Relieves {saved_h}h of workload pressure",
                )

                # Remedy 3: Defer or Drop Task
                if task.priority in ("normal", "low"):
                    remedy_alt = RemedyOption(
                        action="drop_task",
                        task_id=task.id,
                        title="Drop or cancel task",
                        description=f"Remove '{task.title}' from the active horizon to preserve critical goals",
                        parameters={"task_id": task.id},
                        impact_hours=needed_h,
                        impact_description=f"Recovers full {needed_h}h capacity",
                    )
                else:
                    remedy_alt = RemedyOption(
                        action="defer_task",
                        task_id=task.id,
                        title="Defer to next sprint",
                        description="Postpone task to next week's planning horizon",
                        parameters={
                            "task_id": task.id,
                            "target_date": (deadline_user.date() + timedelta(days=7)).isoformat(),
                        },
                        impact_hours=needed_h,
                        impact_description=f"Defers {needed_h}h into next week",
                    )

                problems.append(
                    WorkloadProblem(
                        id=problem_id,
                        task_id=task.id,
                        problem_type="deadline_deficit",
                        description=desc,
                        severity="critical",
                        hours_needed=needed_h,
                        hours_available=avail_h,
                        remedies=[remedy_extend, remedy_reduce, remedy_alt],
                    )
                )

    # Problem Category B: Daily Overloads (Committed hours > 100%)
    for over_day in daily_overloaded_days:
        overage_mins = over_day.total_committed_minutes - over_day.capacity_minutes
        overage_h = round(overage_mins / 60.0, 1)
        committed_h = round(over_day.total_committed_minutes / 60.0, 1)
        cap_h = round(over_day.capacity_minutes / 60.0, 1)

        problem_id = f"prob_overload_{over_day.date}"
        desc = (
            f"{over_day.day_of_week} ({over_day.date}) is overbooked at {over_day.load_percentage:.1f}% "
            f"({committed_h}h / {cap_h}h, {overage_h}h excess)"
        )

        day_blocks = date_blocks_map.get(over_day.date, [])
        first_task_id = day_blocks[-1].task_id if day_blocks else None

        # Remedies for daily overload
        # 1. Add time block (expand boundary)
        remedy_add_time = RemedyOption(
            action="add_time_block",
            task_id=None,
            title="Expand working window",
            description=f"Extend working hours on {over_day.day_of_week} by {int(overage_mins)} minutes",
            parameters={
                "date": over_day.date,
                "additional_minutes": int(overage_mins),
            },
            impact_hours=overage_h,
            impact_description=f"Absorbs the {overage_h}h daily excess",
        )

        # 2. Defer task from this day
        # Find lightest day in the horizon to shift to
        lightest_day = min(daily_loads, key=lambda d: d.load_percentage)
        remedy_defer = RemedyOption(
            action="defer_task",
            task_id=first_task_id,
            title=f"Shift task to {lightest_day.day_of_week}",
            description=f"Rebalance load by shifting work from {over_day.day_of_week} to {lightest_day.day_of_week} ({lightest_day.load_percentage:.0f}% load)",
            parameters={
                "task_id": first_task_id,
                "target_date": lightest_day.date,
            },
            impact_hours=overage_h,
            impact_description=f"Reduces {over_day.day_of_week} load below 100%",
        )

        # 3. Reduce scope across day
        remedy_reduce = RemedyOption(
            action="reduce_scope",
            task_id=first_task_id,
            title="Compress task durations",
            description="Trim estimated focus duration by 15-30% to fit within working limits",
            parameters={"task_id": first_task_id, "reduction_percentage": 25},
            impact_hours=round(committed_h * 0.25, 1),
            impact_description=f"Saves ~{round(committed_h * 0.25, 1)}h across the day",
        )

        problems.append(
            WorkloadProblem(
                id=problem_id,
                task_id=first_task_id,
                problem_type="daily_overload",
                description=desc,
                severity="critical" if over_day.load_percentage >= 120.0 else "warning",
                hours_needed=committed_h,
                hours_available=cap_h,
                remedies=[remedy_defer, remedy_add_time, remedy_reduce],
            )
        )

    # Problem Category C: Tasks scheduled past deadline (At-risk)
    for block in all_blocks:
        if block.is_at_risk:
            task_match = next((t for t in all_tasks if t.id == block.task_id), None)
            task_title = task_match.title if task_match else block.title
            problem_id = f"prob_at_risk_{block.id}"

            # Only add if not already flagged under deficit
            if not any(p.task_id == block.task_id and p.problem_type == "deadline_deficit" for p in problems):
                desc = f"Block '{block.title}' for task '{task_title}' is scheduled past its deadline (at risk)"
                remedy_ext = RemedyOption(
                    action="extend_deadline",
                    task_id=block.task_id,
                    title="Acknowledge & extend deadline",
                    description="Formally extend deadline to match actual scheduled completion time",
                    parameters={
                        "task_id": block.task_id,
                        "suggested_deadline": block.end_time.isoformat(),
                    },
                    impact_hours=round((block.end_time - block.start_time).total_seconds() / 3600.0, 1),
                    impact_description="Eliminates schedule breach",
                )
                remedy_drop = RemedyOption(
                    action="drop_task",
                    task_id=block.task_id,
                    title="Drop or cancel overdue task",
                    description="Cancel task if business requirements no longer justify completion",
                    parameters={"task_id": block.task_id},
                    impact_hours=round((block.end_time - block.start_time).total_seconds() / 3600.0, 1),
                    impact_description="Frees up overdue focus slot",
                )
                problems.append(
                    WorkloadProblem(
                        id=problem_id,
                        task_id=block.task_id,
                        problem_type="at_risk_overflow",
                        description=desc,
                        severity="warning",
                        remedies=[remedy_ext, remedy_drop],
                    )
                )

    # 3. Overall Realism Score Calculation (0 - 100)
    score = 100

    for prob in problems:
        if prob.severity == "critical":
            score -= 15
        elif prob.severity == "warning":
            score -= 10
        else:
            score -= 5

    for over_day in daily_overloaded_days:
        excess_pct = max(0.0, over_day.load_percentage - 100.0)
        score -= min(15, int(excess_pct // 5))

    for tight_day in tight_days:
        score -= 4

    score = max(0, min(100, score))

    if score >= 85:
        status_str = "realistic"
    elif score >= 70:
        status_str = "tight"
    elif score >= 45:
        status_str = "overloaded"
    else:
        status_str = "critical"

    total_sched_h = round(sum(d.scheduled_minutes for d in daily_loads) / 60.0, 1)
    total_cap_h = round(sum(d.capacity_minutes for d in daily_loads) / 60.0, 1)
    total_fe_h = round(sum(d.fixed_event_minutes for d in daily_loads) / 60.0, 1)

    return WorkloadAnalysisResult(
        realism_score=score,
        status=status_str,
        daily_loads=daily_loads,
        problems=problems,
        total_scheduled_hours=total_sched_h,
        total_capacity_hours=total_cap_h,
        total_fixed_event_hours=total_fe_h,
    )
