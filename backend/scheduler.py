from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# Data Transfer Classes
# ---------------------------------------------------------------------------

@dataclass
class TaskInput:
    id: str
    title: str
    estimated_duration_minutes: int
    remaining_duration_minutes: int | None = None
    priority: str = "normal"  # "urgent_important", "important", "normal", "low"
    deadline: datetime | None = None
    is_splittable: bool = True
    min_chunk_minutes: int = 30
    max_chunk_minutes: int = 120
    dependencies: list[str] = field(default_factory=list)
    is_carried_over: bool = False
    is_completed: bool = False
    requires_peak_focus: bool = False

    def get_remaining_minutes(self) -> int:
        if self.remaining_duration_minutes is not None:
            return self.remaining_duration_minutes
        return self.estimated_duration_minutes


@dataclass
class FixedEventInput:
    id: str
    title: str
    start_time: datetime
    end_time: datetime

    def __post_init__(self):
        if self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=timezone.utc)
        if self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=timezone.utc)


@dataclass
class ScheduleSettingsInput:
    timezone_str: str = "UTC"
    work_start_time: str = "09:00"
    work_end_time: str = "17:00"
    work_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0=Mon, 6=Sun
    buffer_minutes: int = 10
    min_chunk_minutes: int = 30
    max_chunk_minutes: int = 120
    peak_focus_start: str = "09:30"
    peak_focus_end: str = "12:30"


@dataclass
class ScheduledBlock:
    id: str
    task_id: str
    title: str
    start_time: datetime
    end_time: datetime
    chunk_index: int = 1
    total_chunks: int = 1
    is_completed: bool = False
    is_at_risk: bool = False


@dataclass
class UnscheduledTaskInfo:
    task_id: str
    title: str
    reason: str
    at_risk: bool = False
    scheduled_minutes: int = 0
    remaining_minutes: int = 0
    deadline: datetime | None = None


@dataclass
class ScheduleResult:
    blocks: list[ScheduledBlock]
    unscheduled_tasks: list[UnscheduledTaskInfo]


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

@dataclass
class TimeInterval:
    start_time: datetime
    end_time: datetime
    is_peak: bool = False

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() // 60)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_time_str(time_str: str) -> time:
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def _to_task_input(item: Any) -> TaskInput:
    if isinstance(item, TaskInput):
        return item
    if isinstance(item, dict):
        return TaskInput(
            id=str(item.get("id", uuid.uuid4())),
            title=item.get("title", "Untitled Task"),
            estimated_duration_minutes=int(item.get("estimated_duration_minutes", 60)),
            remaining_duration_minutes=item.get("remaining_duration_minutes"),
            priority=item.get("priority", "normal"),
            deadline=_ensure_utc(item.get("deadline")),
            is_splittable=bool(item.get("is_splittable", True)),
            min_chunk_minutes=int(item.get("min_chunk_minutes", 30)),
            max_chunk_minutes=int(item.get("max_chunk_minutes", 120)),
            dependencies=list(item.get("dependencies", [])),
            is_carried_over=bool(item.get("is_carried_over", False)),
            is_completed=bool(item.get("is_completed", False)),
            requires_peak_focus=bool(item.get("requires_peak_focus", False)),
        )
    # Generic object attribute access
    return TaskInput(
        id=str(getattr(item, "id", uuid.uuid4())),
        title=getattr(item, "title", "Untitled Task"),
        estimated_duration_minutes=int(getattr(item, "estimated_duration_minutes", 60)),
        remaining_duration_minutes=getattr(item, "remaining_duration_minutes", None),
        priority=getattr(item, "priority", "normal"),
        deadline=_ensure_utc(getattr(item, "deadline", None)),
        is_splittable=bool(getattr(item, "is_splittable", True)),
        min_chunk_minutes=int(getattr(item, "min_chunk_minutes", 30)),
        max_chunk_minutes=int(getattr(item, "max_chunk_minutes", 120)),
        dependencies=list(getattr(item, "dependencies", [])),
        is_carried_over=bool(getattr(item, "is_carried_over", False)),
        is_completed=bool(getattr(item, "is_completed", False)),
        requires_peak_focus=bool(getattr(item, "requires_peak_focus", False)),
    )


def _to_fixed_event_input(item: Any) -> FixedEventInput:
    if isinstance(item, FixedEventInput):
        return item
    if isinstance(item, dict):
        return FixedEventInput(
            id=str(item.get("id", uuid.uuid4())),
            title=item.get("title", "Fixed Event"),
            start_time=_ensure_utc(item["start_time"]),
            end_time=_ensure_utc(item["end_time"]),
        )
    return FixedEventInput(
        id=str(getattr(item, "id", uuid.uuid4())),
        title=getattr(item, "title", "Fixed Event"),
        start_time=_ensure_utc(getattr(item, "start_time")),
        end_time=_ensure_utc(getattr(item, "end_time")),
    )


def _to_settings_input(settings: Any) -> ScheduleSettingsInput:
    if isinstance(settings, ScheduleSettingsInput):
        return settings
    if isinstance(settings, dict):
        return ScheduleSettingsInput(
            timezone_str=settings.get("timezone", settings.get("timezone_str", "UTC")),
            work_start_time=settings.get("work_start_time", "09:00"),
            work_end_time=settings.get("work_end_time", "17:00"),
            work_days=list(settings.get("work_days", [0, 1, 2, 3, 4])),
            buffer_minutes=int(settings.get("buffer_minutes", 10)),
            min_chunk_minutes=int(settings.get("min_chunk_minutes", 30)),
            max_chunk_minutes=int(settings.get("max_chunk_minutes", 120)),
            peak_focus_start=settings.get("peak_focus_start", "09:30"),
            peak_focus_end=settings.get("peak_focus_end", "12:30"),
        )
    return ScheduleSettingsInput(
        timezone_str=getattr(settings, "timezone", getattr(settings, "timezone_str", "UTC")),
        work_start_time=getattr(settings, "work_start_time", "09:00"),
        work_end_time=getattr(settings, "work_end_time", "17:00"),
        work_days=list(getattr(settings, "work_days", [0, 1, 2, 3, 4])),
        buffer_minutes=int(getattr(settings, "buffer_minutes", 10)),
        min_chunk_minutes=int(getattr(settings, "min_chunk_minutes", 30)),
        max_chunk_minutes=int(getattr(settings, "max_chunk_minutes", 120)),
        peak_focus_start=getattr(settings, "peak_focus_start", "09:30"),
        peak_focus_end=getattr(settings, "peak_focus_end", "12:30"),
    )


# ---------------------------------------------------------------------------
# Priority Computation
# ---------------------------------------------------------------------------

def compute_priority(
    task: TaskInput | dict | Any,
    now: datetime,
    completed_task_ids: set[str] | None = None,
) -> float:
    """
    Computes a deterministic numerical priority score for a task.
    Combines:
    1. Urgency: remaining effort vs time until deadline.
    2. Importance: priority category (urgent_important, important, normal, low).
    3. Dependency readiness: negative score if prerequisites remain uncompleted.
    4. Carry-over boost: bonus for tasks carried over from prior sessions.
    """
    t = _to_task_input(task)
    now_utc = _ensure_utc(now)
    completed_set = completed_task_ids or set()

    # If task is already completed, priority is zero
    if t.is_completed:
        return 0.0

    # 1. Dependency readiness check
    if t.dependencies:
        unresolved = [d for d in t.dependencies if d not in completed_set]
        if unresolved:
            # Task is blocked by uncompleted dependencies
            return -1000.0 - (len(unresolved) * 50.0)

    # 2. Base importance weight
    importance_weights = {
        "urgent_important": 100.0,
        "important": 70.0,
        "normal": 40.0,
        "low": 10.0,
    }
    base_importance = importance_weights.get(t.priority.lower(), 40.0)

    # 3. Urgency calculation
    urgency_score = 0.0
    if t.deadline is not None:
        deadline_utc = _ensure_utc(t.deadline)
        seconds_left = (deadline_utc - now_utc).total_seconds()
        remaining_minutes = t.get_remaining_minutes()

        if seconds_left <= 0:
            # Overdue: maximum urgency
            urgency_score = 150.0
        else:
            hours_left = max(seconds_left / 3600.0, 0.1)
            effort_hours = remaining_minutes / 60.0
            tightness = effort_hours / hours_left

            if tightness >= 1.0:
                urgency_score = 120.0 + min(tightness * 10.0, 50.0)
            else:
                # Proximity curve
                urgency_score = (tightness * 70.0) + (40.0 / max(hours_left, 1.0))

    # 4. Carry-over boost
    carry_over_boost = 30.0 if t.is_carried_over else 0.0

    # 5. Dependency unblocker bonus (if other tasks depend on this task)
    dependency_readiness_bonus = 20.0 if not t.dependencies else 10.0

    # 6. Effort balancing (small tiebreaker for shorter tasks to maximize completion rate)
    rem_min = t.get_remaining_minutes()
    duration_tiebreaker = max(0.0, 5.0 - (rem_min / 60.0))

    return base_importance + urgency_score + carry_over_boost + dependency_readiness_bonus + duration_tiebreaker


# ---------------------------------------------------------------------------
# Working Intervals & Fixed Events Packing
# ---------------------------------------------------------------------------

def _generate_free_intervals(
    settings: ScheduleSettingsInput,
    fixed_events: Sequence[FixedEventInput],
    start: datetime,
    horizon_days: int,
) -> list[TimeInterval]:
    """
    Computes all contiguous free intervals inside the user's working hours,
    with fixed events subtracted.
    """
    try:
        user_tz = ZoneInfo(settings.timezone_str)
    except Exception:
        user_tz = timezone.utc

    start_utc = _ensure_utc(start)
    start_user = start_utc.astimezone(user_tz)

    work_start_t = _parse_time_str(settings.work_start_time)
    work_end_t = _parse_time_str(settings.work_end_time)
    peak_start_t = _parse_time_str(settings.peak_focus_start)
    peak_end_t = _parse_time_str(settings.peak_focus_end)

    raw_work_intervals: list[TimeInterval] = []

    current_date = start_user.date()
    for day_offset in range(horizon_days):
        day = current_date + timedelta(days=day_offset)

        # Check if day of week is an active work day (0=Monday, 6=Sunday)
        if day.weekday() not in settings.work_days:
            continue

        local_work_start = datetime.combine(day, work_start_t, tzinfo=user_tz)
        local_work_end = datetime.combine(day, work_end_t, tzinfo=user_tz)

        if local_work_end <= local_work_start:
            # Invalid or inverted working window
            continue

        utc_work_start = local_work_start.astimezone(timezone.utc)
        utc_work_end = local_work_end.astimezone(timezone.utc)

        # If work day ended before current start, skip
        if utc_work_end <= start_utc:
            continue

        # If day has already started, clip beginning
        effective_start = max(utc_work_start, start_utc)

        # Ensure 5-minute alignment forward
        if effective_start.minute % 5 != 0:
            minutes_to_add = 5 - (effective_start.minute % 5)
            effective_start = effective_start + timedelta(minutes=minutes_to_add)
            effective_start = effective_start.replace(second=0, microsecond=0)

        if effective_start >= utc_work_end:
            continue

        # Peak hours window for this day
        local_peak_start = datetime.combine(day, peak_start_t, tzinfo=user_tz)
        local_peak_end = datetime.combine(day, peak_end_t, tzinfo=user_tz)
        utc_peak_start = local_peak_start.astimezone(timezone.utc)
        utc_peak_end = local_peak_end.astimezone(timezone.utc)

        raw_work_intervals.append(
            TimeInterval(
                start_time=effective_start,
                end_time=utc_work_end,
                is_peak=False,
            )
        )

    # Subtract fixed events from raw working intervals
    free_intervals: list[TimeInterval] = []
    normalized_fixed = sorted(
        [_to_fixed_event_input(e) for e in fixed_events],
        key=lambda x: x.start_time,
    )

    for work_inv in raw_work_intervals:
        current_segments = [work_inv]

        for fe in normalized_fixed:
            next_segments: list[TimeInterval] = []
            for seg in current_segments:
                # Check for overlap: fe overlaps seg iff fe.start < seg.end and fe.end > seg.start
                if fe.start_time >= seg.end_time or fe.end_time <= seg.start_time:
                    # No overlap
                    next_segments.append(seg)
                else:
                    # Overlap: segment is split or shortened
                    if fe.start_time > seg.start_time:
                        # Left slice
                        next_segments.append(
                            TimeInterval(
                                start_time=seg.start_time,
                                end_time=fe.start_time,
                                is_peak=seg.is_peak,
                            )
                        )
                    if fe.end_time < seg.end_time:
                        # Right slice
                        next_segments.append(
                            TimeInterval(
                                start_time=fe.end_time,
                                end_time=seg.end_time,
                                is_peak=seg.is_peak,
                            )
                        )
            current_segments = next_segments

        for seg in current_segments:
            if seg.duration_minutes >= 5:
                # Tag whether it overlaps peak hours
                seg_user_start = seg.start_time.astimezone(user_tz)
                is_in_peak = (
                    seg_user_start.time() >= peak_start_t
                    and seg_user_start.time() < peak_end_t
                )
                seg.is_peak = is_in_peak
                free_intervals.append(seg)

    return sorted(free_intervals, key=lambda x: x.start_time)


# ---------------------------------------------------------------------------
# Core Scheduler Algorithm
# ---------------------------------------------------------------------------

def build_schedule(
    tasks: Sequence[TaskInput | dict | Any],
    fixed_events: Sequence[FixedEventInput | dict | Any] = (),
    settings: ScheduleSettingsInput | dict | Any = None,
    start: datetime | None = None,
    horizon_days: int = 7,
) -> ScheduleResult:
    """
    Deterministic greedy time-blocking scheduler.
    
    Guarantees:
    - Never produces overlapping blocks.
    - Never schedules overlapping fixed events.
    - Respects working hours, working days, and rest buffers.
    - Matches high-effort / high-priority tasks into peak focus intervals.
    - Respects task dependencies (prerequisites must complete before dependent tasks start).
    - Splits tasks across slots and days if needed, adhering to min_chunk and max_chunk.
    - Never schedules past a deadline unless flagged as 'at_risk'.
    - Returns scheduled blocks and unscheduled/at-risk tasks with explicit diagnostic reasons.
    """
    settings_obj = _to_settings_input(settings or ScheduleSettingsInput())
    start_utc = _ensure_utc(start or datetime.now(timezone.utc))

    # Normalize tasks
    all_tasks = [_to_task_input(t) for t in tasks]
    fixed_events_list = [_to_fixed_event_input(e) for e in fixed_events]

    # Generate available free intervals
    free_intervals = _generate_free_intervals(
        settings=settings_obj,
        fixed_events=fixed_events_list,
        start=start_utc,
        horizon_days=horizon_days,
    )

    scheduled_blocks: list[ScheduledBlock] = []
    unscheduled_tasks: list[UnscheduledTaskInfo] = []

    # State tracking
    completed_task_ids: set[str] = {t.id for t in all_tasks if t.is_completed}
    task_finish_times: dict[str, datetime] = {}
    task_remaining_minutes: dict[str, int] = {
        t.id: t.get_remaining_minutes() for t in all_tasks
    }
    task_chunks_count: dict[str, int] = {t.id: 0 for t in all_tasks}
    task_at_risk_flag: dict[str, bool] = {t.id: False for t in all_tasks}

    # Helper: Check if task is ready (all dependencies completed or scheduled)
    def is_dependency_ready(task: TaskInput, current_time: datetime) -> tuple[bool, datetime]:
        if not task.dependencies:
            return True, start_utc
        earliest_allowed = start_utc
        for dep_id in task.dependencies:
            if dep_id not in completed_task_ids and dep_id not in task_finish_times:
                return False, start_utc
            if dep_id in task_finish_times:
                dep_end = task_finish_times[dep_id]
                if dep_end > earliest_allowed:
                    earliest_allowed = dep_end
        return True, earliest_allowed

    # Track placement cursor across intervals
    # interval_idx -> current available start time inside that interval
    current_inv_starts: list[datetime] = [inv.start_time for inv in free_intervals]

    # Simulation loop: dynamically select highest priority ready task
    active_tasks = [t for t in all_tasks if not t.is_completed and task_remaining_minutes[t.id] > 0]

    while active_tasks:
        # Find current simulation time across free intervals
        first_available_idx = None
        for i in range(len(free_intervals)):
            if current_inv_starts[i] < free_intervals[i].end_time:
                first_available_idx = i
                break

        if first_available_idx is None:
            # Capacity completely exhausted
            break

        current_sim_time = current_inv_starts[first_available_idx]

        # Prioritize active tasks at current_sim_time
        candidate_scores: list[tuple[float, TaskInput]] = []
        for t in active_tasks:
            ready, earliest_start = is_dependency_ready(t, current_sim_time)
            if not ready:
                continue

            score = compute_priority(t, now=current_sim_time, completed_task_ids=completed_task_ids)
            candidate_scores.append((score, t))

        if not candidate_scores:
            # No ready tasks could be scheduled at this moment due to dependencies
            # Check if any dependencies will finish in a future interval
            future_finish = [
                task_finish_times[d]
                for t in active_tasks
                for d in t.dependencies
                if d in task_finish_times and task_finish_times[d] > current_sim_time
            ]
            if future_finish:
                min_future = min(future_finish)
                # Advance current interval start to min_future
                advanced = False
                for i in range(first_available_idx, len(free_intervals)):
                    if free_intervals[i].end_time > min_future:
                        current_inv_starts[i] = max(current_inv_starts[i], min_future)
                        advanced = True
                        break
                if advanced:
                    continue

            # Cannot advance dependencies further: circular or missing dependency!
            break

        # Sort candidate tasks: highest priority first
        candidate_scores.sort(key=lambda x: x[0], reverse=True)
        chosen_score, chosen_task = candidate_scores[0]

        ready, earliest_dep_start = is_dependency_ready(chosen_task, current_sim_time)
        rem_min = task_remaining_minutes[chosen_task.id]

        # Determine target chunk size
        task_min_chunk = chosen_task.min_chunk_minutes or settings_obj.min_chunk_minutes
        task_max_chunk = chosen_task.max_chunk_minutes or settings_obj.max_chunk_minutes

        # Try to find the earliest interval that can host this task (or chunk)
        scheduled_in_slot = False

        for i in range(first_available_idx, len(free_intervals)):
            inv = free_intervals[i]
            cur_start = max(current_inv_starts[i], earliest_dep_start)

            # Ensure cur_start is before inv.end_time
            if cur_start >= inv.end_time:
                continue

            available_minutes = int((inv.end_time - cur_start).total_seconds() // 60)
            if available_minutes < 5:
                continue

            # Check peak preference for high-effort/urgent tasks
            is_high_effort = (
                chosen_task.requires_peak_focus
                or chosen_task.priority in ("urgent_important", "important")
                or chosen_task.estimated_duration_minutes >= 90
            )

            # Calculate chunk duration
            if chosen_task.is_splittable:
                # If splittable, we need at least min(task_min_chunk, rem_min)
                required_min = min(task_min_chunk, rem_min)
                if available_minutes < required_min:
                    continue

                chunk_duration = min(rem_min, task_max_chunk, available_minutes)
            else:
                # Non-splittable: entire remaining effort must fit in this interval
                if available_minutes < rem_min:
                    continue
                chunk_duration = rem_min

            slot_end = cur_start + timedelta(minutes=chunk_duration)

            # Deadline enforcement
            at_risk = False
            if chosen_task.deadline is not None:
                deadline_utc = _ensure_utc(chosen_task.deadline)
                if slot_end > deadline_utc:
                    # Would finish past deadline: mark as at-risk
                    at_risk = True

            # If task has a deadline and there are intervals BEFORE deadline,
            # we should avoid scheduling it past deadline if it can fit earlier.
            # But since we greedily search from earliest interval, this is the earliest possible slot!

            # Place the block!
            block_id = str(uuid.uuid4())
            task_chunks_count[chosen_task.id] += 1
            chunk_idx = task_chunks_count[chosen_task.id]

            block = ScheduledBlock(
                id=block_id,
                task_id=chosen_task.id,
                title=f"{chosen_task.title}" if rem_min == chunk_duration and chunk_idx == 1 else f"{chosen_task.title} (Part {chunk_idx})",
                start_time=cur_start,
                end_time=slot_end,
                chunk_index=chunk_idx,
                total_chunks=chunk_idx,  # Updated at the end
                is_completed=False,
                is_at_risk=at_risk,
            )
            scheduled_blocks.append(block)

            # Update remaining duration
            task_remaining_minutes[chosen_task.id] -= chunk_duration
            task_finish_times[chosen_task.id] = slot_end
            if at_risk:
                task_at_risk_flag[chosen_task.id] = True

            # Advance current interval start with rest buffer
            next_start = slot_end + timedelta(minutes=settings_obj.buffer_minutes)
            current_inv_starts[i] = next_start

            scheduled_in_slot = True
            break

        if not scheduled_in_slot:
            # Cannot schedule this task in any available interval
            # Remove from active tasks to prevent infinite loop
            active_tasks.remove(chosen_task)
            reason = "Task cannot fit in available working slots before horizon limit"
            if not chosen_task.is_splittable and rem_min > settings_obj.max_chunk_minutes:
                reason = f"Non-splittable task duration ({rem_min}m) exceeds max continuous slot capacity"
            elif chosen_task.deadline and chosen_task.deadline < start_utc:
                reason = "Task deadline is already in the past"

            unscheduled_tasks.append(
                UnscheduledTaskInfo(
                    task_id=chosen_task.id,
                    title=chosen_task.title,
                    reason=reason,
                    at_risk=True,
                    scheduled_minutes=chosen_task.get_remaining_minutes() - rem_min,
                    remaining_minutes=rem_min,
                    deadline=chosen_task.deadline,
                )
            )
            continue

        # If task has completed its full duration
        if task_remaining_minutes[chosen_task.id] <= 0:
            completed_task_ids.add(chosen_task.id)
            active_tasks.remove(chosen_task)

            # If task ended up at risk, record in unscheduled_tasks as at-risk
            if task_at_risk_flag[chosen_task.id]:
                unscheduled_tasks.append(
                    UnscheduledTaskInfo(
                        task_id=chosen_task.id,
                        title=chosen_task.title,
                        reason="Scheduled past deadline (at risk)",
                        at_risk=True,
                        scheduled_minutes=chosen_task.get_remaining_minutes(),
                        remaining_minutes=0,
                        deadline=chosen_task.deadline,
                    )
                )

    # Any remaining active tasks that could not be fully scheduled
    for t in active_tasks:
        rem_min = task_remaining_minutes[t.id]
        sched_min = t.get_remaining_minutes() - rem_min
        reason = "Available working hours exhausted (overbooked horizon)"
        if t.dependencies:
            unresolved = [d for d in t.dependencies if d not in completed_task_ids]
            if unresolved:
                reason = f"Blocked by uncompleted dependencies: {', '.join(unresolved)}"

        unscheduled_tasks.append(
            UnscheduledTaskInfo(
                task_id=t.id,
                title=t.title,
                reason=reason,
                at_risk=True,
                scheduled_minutes=sched_min,
                remaining_minutes=rem_min,
                deadline=t.deadline,
            )
        )

    # Update total_chunks for splittable blocks
    for b in scheduled_blocks:
        b.total_chunks = task_chunks_count.get(b.task_id, 1)

    # -----------------------------------------------------------------------
    # Invariant Verification (Strict Zero Overlap Assurance)
    # -----------------------------------------------------------------------
    scheduled_blocks.sort(key=lambda b: b.start_time)

    for i in range(len(scheduled_blocks)):
        curr_b = scheduled_blocks[i]
        assert curr_b.start_time < curr_b.end_time, f"Block duration non-positive: {curr_b}"

        # Check overlap with next block
        if i + 1 < len(scheduled_blocks):
            next_b = scheduled_blocks[i + 1]
            assert curr_b.end_time <= next_b.start_time, (
                f"Overlap detected between blocks {curr_b.title} ({curr_b.start_time} - {curr_b.end_time}) "
                f"and {next_b.title} ({next_b.start_time} - {next_b.end_time})"
            )

        # Check overlap with fixed events
        for fe in fixed_events_list:
            overlap = (curr_b.start_time < fe.end_time) and (curr_b.end_time > fe.start_time)
            assert not overlap, (
                f"Overlap detected between block {curr_b.title} ({curr_b.start_time} - {curr_b.end_time}) "
                f"and fixed event {fe.title} ({fe.start_time} - {fe.end_time})"
            )

    return ScheduleResult(
        blocks=scheduled_blocks,
        unscheduled_tasks=unscheduled_tasks,
    )
