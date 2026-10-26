from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from scheduler import (
    TaskInput,
    FixedEventInput,
    ScheduleSettingsInput,
    ScheduledBlock,
    UnscheduledTaskInfo,
    ScheduleResult,
    compute_priority,
    build_schedule,
)


# Reference anchor: Monday, October 26, 2026 at 09:00 UTC
ANCHOR_MONDAY = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


def test_1_empty_day_no_tasks_no_events():
    """Empty day produces zero blocks and zero unscheduled tasks."""
    res = build_schedule(
        tasks=[],
        fixed_events=[],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 0
    assert len(res.unscheduled_tasks) == 0


def test_2_single_task_fits_working_hours():
    """Single 60-min task scheduled cleanly at work day start."""
    task = TaskInput(id="t1", title="Write Report", estimated_duration_minutes=60)
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    b = res.blocks[0]
    assert b.task_id == "t1"
    assert b.start_time == ANCHOR_MONDAY
    assert b.end_time == ANCHOR_MONDAY + timedelta(minutes=60)
    assert len(res.unscheduled_tasks) == 0


def test_3_overbooked_day_exceeding_capacity():
    """Overbooked day: total task effort exceeds 8 hours (480 mins). Tasks pack to capacity, overflow marked at risk."""
    tasks = [
        TaskInput(id=f"t{i}", title=f"Task {i}", estimated_duration_minutes=120, priority="normal")
        for i in range(5)  # 5 * 120 = 600 mins > 480 mins in 09:00-17:00
    ]
    res = build_schedule(
        tasks=tasks,
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    # Available time is 480 mins. With 10m buffers between blocks, only 3-4 blocks can fit.
    total_scheduled_minutes = sum((b.end_time - b.start_time).total_seconds() / 60 for b in res.blocks)
    assert total_scheduled_minutes <= 480
    assert len(res.unscheduled_tasks) > 0
    # Overbooked tasks have at_risk flag
    assert any(u.at_risk for u in res.unscheduled_tasks)


def test_4_dependency_chain_sequential_placement():
    """Task A -> Task B -> Task C: B cannot start before A finishes, C cannot start before B finishes."""
    task_a = TaskInput(id="a", title="Design Schema", estimated_duration_minutes=60)
    task_b = TaskInput(id="b", title="Implement Backend", estimated_duration_minutes=60, dependencies=["a"])
    task_c = TaskInput(id="c", title="Frontend Connect", estimated_duration_minutes=60, dependencies=["b"])

    res = build_schedule(
        tasks=[task_a, task_b, task_c],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 3
    block_map = {b.task_id: b for b in res.blocks}

    # Verify chronological dependency ordering with buffer
    assert block_map["b"].start_time >= block_map["a"].end_time
    assert block_map["c"].start_time >= block_map["b"].end_time


def test_5_deadline_today_imminent_prioritization():
    """Task with impending deadline today gets scheduled before a normal task without a deadline."""
    task_normal = TaskInput(
        id="t_normal",
        title="Casual Refactor",
        estimated_duration_minutes=60,
        priority="important",
    )
    task_urgent_deadline = TaskInput(
        id="t_deadline",
        title="Fix Critical Bug",
        estimated_duration_minutes=60,
        priority="normal",
        deadline=ANCHOR_MONDAY + timedelta(hours=2),  # Due in 2 hours!
    )

    res = build_schedule(
        tasks=[task_normal, task_urgent_deadline],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 2
    # The deadline task must be scheduled first
    assert res.blocks[0].task_id == "t_deadline"
    assert res.blocks[0].end_time <= task_urgent_deadline.deadline


def test_6_task_longer_than_any_slot_splits_across_slots():
    """A 240-min task with 120-min max chunk splits across multiple chunks."""
    task = TaskInput(
        id="big_task",
        title="Massive Feature",
        estimated_duration_minutes=240,
        is_splittable=True,
        max_chunk_minutes=120,
        min_chunk_minutes=30,
    )
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 2  # 120m + 120m = 240m
    assert res.blocks[0].chunk_index == 1
    assert res.blocks[0].total_chunks == 2
    assert res.blocks[1].chunk_index == 2
    assert res.blocks[1].total_chunks == 2
    assert (res.blocks[0].end_time - res.blocks[0].start_time).total_seconds() == 120 * 60
    assert (res.blocks[1].end_time - res.blocks[1].start_time).total_seconds() == 120 * 60


def test_7_fixed_events_splitting_the_day():
    """Meetings at 10:00-10:30 and 12:00-13:00 divide working hours; tasks pack cleanly around them."""
    meeting1 = FixedEventInput(
        id="m1",
        title="Team Standup",
        start_time=ANCHOR_MONDAY + timedelta(hours=1),  # 10:00
        end_time=ANCHOR_MONDAY + timedelta(hours=1, minutes=30),  # 10:30
    )
    meeting2 = FixedEventInput(
        id="m2",
        title="Lunch & Learn",
        start_time=ANCHOR_MONDAY + timedelta(hours=3),  # 12:00
        end_time=ANCHOR_MONDAY + timedelta(hours=4),  # 13:00
    )
    tasks = [
        TaskInput(id="t1", title="Task 1", estimated_duration_minutes=60),
        TaskInput(id="t2", title="Task 2", estimated_duration_minutes=90),
    ]

    res = build_schedule(
        tasks=tasks,
        fixed_events=[meeting1, meeting2],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) >= 2

    # Verify no block overlaps meeting 1 or meeting 2
    for b in res.blocks:
        assert not (b.start_time < meeting1.end_time and b.end_time > meeting1.start_time)
        assert not (b.start_time < meeting2.end_time and b.end_time > meeting2.start_time)


def test_8_rest_buffer_between_consecutive_blocks():
    """Verify that buffer_minutes (e.g. 15 mins) is enforced between consecutive tasks."""
    settings = ScheduleSettingsInput(buffer_minutes=15)
    t1 = TaskInput(id="t1", title="Task 1", estimated_duration_minutes=45)
    t2 = TaskInput(id="t2", title="Task 2", estimated_duration_minutes=45)

    res = build_schedule(
        tasks=[t1, t2],
        settings=settings,
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 2
    b1, b2 = res.blocks[0], res.blocks[1]
    # Difference between b1 end and b2 start must be at least 15 minutes
    gap_minutes = (b2.start_time - b1.end_time).total_seconds() / 60
    assert gap_minutes >= 15


def test_9_non_splittable_task_fitting():
    """Non-splittable 90m task fits in a 120m window cleanly."""
    task = TaskInput(
        id="unsplittable",
        title="Deep Math Proof",
        estimated_duration_minutes=90,
        is_splittable=False,
    )
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    assert (res.blocks[0].end_time - res.blocks[0].start_time).total_seconds() == 90 * 60


def test_10_non_splittable_task_too_large_for_any_slot():
    """Non-splittable task that is longer than available working day (500 mins vs 480 mins) is flagged unscheduled."""
    task = TaskInput(
        id="huge_unsplittable",
        title="Unsplittable Marathon",
        estimated_duration_minutes=500,
        is_splittable=False,
    )
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 0
    assert len(res.unscheduled_tasks) == 1
    assert res.unscheduled_tasks[0].task_id == "huge_unsplittable"
    assert "exceeds" in res.unscheduled_tasks[0].reason.lower()


def test_11_peak_focus_preference_high_effort():
    """High-effort urgent task gets scheduled during morning/peak hours over casual low task."""
    urgent_heavy = TaskInput(
        id="heavy",
        title="Kernel Optimization",
        estimated_duration_minutes=120,
        priority="urgent_important",
        requires_peak_focus=True,
    )
    low_short = TaskInput(
        id="light",
        title="Clean Desktop",
        estimated_duration_minutes=30,
        priority="low",
    )
    res = build_schedule(
        tasks=[low_short, urgent_heavy],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert res.blocks[0].task_id == "heavy"


def test_12_carry_over_boost_increases_priority():
    """Carried over task gets a higher priority score than identical fresh task."""
    fresh = TaskInput(id="f", title="Fresh Task", estimated_duration_minutes=60, priority="normal")
    carried = TaskInput(id="c", title="Carried Task", estimated_duration_minutes=60, priority="normal", is_carried_over=True)

    score_fresh = compute_priority(fresh, now=ANCHOR_MONDAY)
    score_carried = compute_priority(carried, now=ANCHOR_MONDAY)
    assert score_carried > score_fresh


def test_13_working_days_weekend_skipping():
    """Starting on Saturday (day 5 of week) skips weekend and schedules on Monday."""
    saturday = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
    task = TaskInput(id="t1", title="Monday Morning Task", estimated_duration_minutes=60)

    # Mon-Fri are days 0,1,2,3,4
    settings = ScheduleSettingsInput(work_days=[0, 1, 2, 3, 4], timezone_str="UTC")
    res = build_schedule(
        tasks=[task],
        settings=settings,
        start=saturday,
        horizon_days=4,
    )
    assert len(res.blocks) == 1
    # Should be scheduled on Monday Oct 26
    assert res.blocks[0].start_time.date() == date(2026, 10, 26)


def test_14_unresolved_dependency_blocked():
    """Task whose dependency is missing is never scheduled and reported in unscheduled_tasks."""
    task = TaskInput(id="dependent", title="Deploy", estimated_duration_minutes=30, dependencies=["missing_dep"])
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 0
    assert len(res.unscheduled_tasks) == 1
    assert "dependencies" in res.unscheduled_tasks[0].reason.lower()


def test_15_circular_dependency_gracefully_handled():
    """Circular dependency A <-> B does not cause infinite loop; both reported in unscheduled."""
    task_a = TaskInput(id="a", title="Task A", estimated_duration_minutes=30, dependencies=["b"])
    task_b = TaskInput(id="b", title="Task B", estimated_duration_minutes=30, dependencies=["a"])

    res = build_schedule(
        tasks=[task_a, task_b],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 0
    assert len(res.unscheduled_tasks) == 2


def test_16_strict_non_overlapping_guarantee():
    """Pack 8 varied tasks with 3 fixed events and verify 100% disjoint blocks."""
    events = [
        FixedEventInput(id="e1", title="Sync", start_time=ANCHOR_MONDAY + timedelta(hours=1), end_time=ANCHOR_MONDAY + timedelta(hours=1, minutes=30)),
        FixedEventInput(id="e2", title="Call", start_time=ANCHOR_MONDAY + timedelta(hours=4), end_time=ANCHOR_MONDAY + timedelta(hours=5)),
    ]
    tasks = [
        TaskInput(id=f"t{i}", title=f"Task {i}", estimated_duration_minutes=45, priority="normal")
        for i in range(8)
    ]
    res = build_schedule(
        tasks=tasks,
        fixed_events=events,
        start=ANCHOR_MONDAY,
        horizon_days=2,
    )
    # Check no two blocks overlap
    for i in range(len(res.blocks)):
        for j in range(i + 1, len(res.blocks)):
            b1 = res.blocks[i]
            b2 = res.blocks[j]
            assert b1.end_time <= b2.start_time or b2.end_time <= b1.start_time

        # Check no block overlaps events
        for e in events:
            assert res.blocks[i].end_time <= e.start_time or res.blocks[i].start_time >= e.end_time


def test_17_fixed_event_completely_covering_work_day():
    """All-day fixed event (09:00 - 17:00) pushes all work to day 2."""
    all_day_conf = FixedEventInput(
        id="conf",
        title="Offsite Hackathon",
        start_time=ANCHOR_MONDAY,
        end_time=ANCHOR_MONDAY + timedelta(hours=8),
    )
    task = TaskInput(id="t1", title="Post-Conf Review", estimated_duration_minutes=60)
    res = build_schedule(
        tasks=[task],
        fixed_events=[all_day_conf],
        start=ANCHOR_MONDAY,
        horizon_days=2,
    )
    assert len(res.blocks) == 1
    # Must be scheduled on Tuesday Oct 27
    assert res.blocks[0].start_time.date() == date(2026, 10, 27)


def test_18_fixed_event_outside_working_hours():
    """Evening fixed event (20:00 - 21:00) does not interfere with 09:00 - 17:00 work blocks."""
    evening_event = FixedEventInput(
        id="dinner",
        title="Networking Dinner",
        start_time=ANCHOR_MONDAY + timedelta(hours=11),  # 20:00 UTC
        end_time=ANCHOR_MONDAY + timedelta(hours=12),
    )
    task = TaskInput(id="t1", title="Day Work", estimated_duration_minutes=120)
    res = build_schedule(
        tasks=[task],
        fixed_events=[evening_event],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    assert res.blocks[0].start_time == ANCHOR_MONDAY


def test_19_timezone_conversion_correctness():
    """User in America/New_York (UTC-4 in Oct) with 09:00-17:00 schedules blocks from 13:00 to 21:00 UTC."""
    settings = ScheduleSettingsInput(
        timezone_str="America/New_York",
        work_start_time="09:00",
        work_end_time="17:00",
    )
    # Start at 08:00 EDT (12:00 UTC)
    start_utc = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    task = TaskInput(id="t1", title="Morning NY Task", estimated_duration_minutes=60)

    res = build_schedule(
        tasks=[task],
        settings=settings,
        start=start_utc,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    # 09:00 EDT = 13:00 UTC
    assert res.blocks[0].start_time == datetime(2026, 10, 26, 13, 0, tzinfo=timezone.utc)


def test_20_completed_tasks_ignored():
    """Tasks marked completed are not scheduled."""
    task = TaskInput(id="done", title="Already Finished", estimated_duration_minutes=60, is_completed=True)
    res = build_schedule(
        tasks=[task],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 0
    assert len(res.unscheduled_tasks) == 0


def test_21_exact_slot_fill():
    """A 60m task in a 60m interval fits exactly without errors."""
    m1 = FixedEventInput(
        id="m1",
        title="Starts at 10",
        start_time=ANCHOR_MONDAY + timedelta(hours=1),
        end_time=ANCHOR_MONDAY + timedelta(hours=8),
    )
    task = TaskInput(id="exact", title="Fill Exact 1hr", estimated_duration_minutes=60)
    res = build_schedule(
        tasks=[task],
        fixed_events=[m1],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    assert res.blocks[0].start_time == ANCHOR_MONDAY
    assert res.blocks[0].end_time == ANCHOR_MONDAY + timedelta(hours=1)


def test_22_at_risk_scheduled_past_deadline():
    """Task scheduled past deadline is flagged with is_at_risk=True."""
    # Deadline is 10:00 AM, but slot from 09:00-10:00 is occupied by a fixed event
    event = FixedEventInput(
        id="blocker",
        title="Early Meeting",
        start_time=ANCHOR_MONDAY,
        end_time=ANCHOR_MONDAY + timedelta(hours=1),
    )
    task = TaskInput(
        id="late_task",
        title="Missed Deadline Task",
        estimated_duration_minutes=60,
        deadline=ANCHOR_MONDAY + timedelta(hours=1),  # Deadline is at 10:00 AM
    )
    res = build_schedule(
        tasks=[task],
        fixed_events=[event],
        start=ANCHOR_MONDAY,
        horizon_days=1,
    )
    assert len(res.blocks) == 1
    assert res.blocks[0].is_at_risk is True
    assert any(u.at_risk for u in res.unscheduled_tasks)
