from datetime import datetime, timedelta, timezone
import pytest

from scheduler import TaskInput, ScheduledBlock, ScheduleSettingsInput, FixedEventInput
from feasibility import analyze_workload, WorkloadAnalysisResult


ANCHOR_NOW = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)  # Monday 09:00 UTC


def test_realistic_workload_high_score():
    """A light, well-spaced workload produces realism score >= 85 and status 'realistic'."""
    settings = ScheduleSettingsInput(
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    # 3 hours of scheduled work in an 8-hour day (37.5% load)
    blocks = [
        ScheduledBlock(
            id="b1",
            task_id="t1",
            title="Focus Session",
            start_time=ANCHOR_NOW,
            end_time=ANCHOR_NOW + timedelta(hours=3),
        )
    ]
    tasks = [
        TaskInput(
            id="t1",
            title="Focus Session",
            estimated_duration_minutes=180,
            remaining_duration_minutes=0,
            deadline=ANCHOR_NOW + timedelta(days=2),
        )
    ]

    res = analyze_workload(
        tasks=tasks,
        schedule=blocks,
        settings=settings,
        now=ANCHOR_NOW,
        horizon_days=5,
    )
    assert res.realism_score >= 85
    assert res.status == "realistic"
    assert len(res.problems) == 0
    assert res.daily_loads[0].load_percentage == 37.5


def test_deadline_deficit_detection_and_remedies():
    """Task needs 6h but only 3.5h free before deadline. Verifies specific problem string and 3 machine-readable remedies."""
    settings = ScheduleSettingsInput(
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    # Deadline is 3.5 hours from start (12:30 UTC)
    deadline = ANCHOR_NOW + timedelta(hours=3, minutes=30)
    task = TaskInput(
        id="tight_task",
        title="Emergency Feature",
        estimated_duration_minutes=360,  # 6.0 hours needed!
        remaining_duration_minutes=360,
        deadline=deadline,
        priority="urgent_important",
    )

    res = analyze_workload(
        tasks=[task],
        schedule=[],
        settings=settings,
        now=ANCHOR_NOW,
        horizon_days=5,
    )
    assert len(res.problems) >= 1
    prob = next(p for p in res.problems if p.problem_type == "deadline_deficit")
    assert "needs 6.0h but only 3.5h free before then" in prob.description
    assert prob.severity == "critical"
    assert prob.hours_needed == 6.0
    assert prob.hours_available == 3.5

    # Check 3 machine-readable remedy options
    assert len(prob.remedies) == 3
    actions = [r.action for r in prob.remedies]
    assert "extend_deadline" in actions
    assert "reduce_scope" in actions

    # Verify remedy parameter structures and computed impact
    extend_remedy = next(r for r in prob.remedies if r.action == "extend_deadline")
    assert "suggested_deadline" in extend_remedy.parameters
    assert extend_remedy.impact_hours == 2.5  # 6.0 - 3.5 = 2.5h deficit
    assert "2.5h" in extend_remedy.impact_description

    reduce_remedy = next(r for r in prob.remedies if r.action == "reduce_scope")
    assert reduce_remedy.parameters["suggested_duration_minutes"] == 210  # 3.5h
    assert reduce_remedy.impact_hours == 2.5


def test_daily_overload_detection_and_remedies():
    """Day with 10 hours of work in an 8-hour window (125% load) triggers daily_overload problem with remedies."""
    settings = ScheduleSettingsInput(
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    # Schedule blocks totaling 10h (600 mins)
    blocks = [
        ScheduledBlock(
            id="b1",
            task_id="t1",
            title="Block 1",
            start_time=ANCHOR_NOW,
            end_time=ANCHOR_NOW + timedelta(hours=5),
        ),
        ScheduledBlock(
            id="b2",
            task_id="t2",
            title="Block 2",
            start_time=ANCHOR_NOW + timedelta(hours=5),
            end_time=ANCHOR_NOW + timedelta(hours=10),
        ),
    ]

    res = analyze_workload(
        tasks=[],
        schedule=blocks,
        settings=settings,
        now=ANCHOR_NOW,
        horizon_days=5,
    )
    assert res.daily_loads[0].is_overloaded is True
    assert res.daily_loads[0].load_percentage == 125.0

    prob = next((p for p in res.problems if p.problem_type == "daily_overload"), None)
    assert prob is not None
    assert "overbooked at 125.0%" in prob.description

    # Remedies must include add_time_block and defer_task
    actions = [r.action for r in prob.remedies]
    assert "add_time_block" in actions
    assert "defer_task" in actions

    add_time = next(r for r in prob.remedies if r.action == "add_time_block")
    assert add_time.parameters["additional_minutes"] == 120  # 2 hours excess
    assert add_time.impact_hours == 2.0


def test_at_risk_overflow_detection():
    """Blocks marked is_at_risk generate an at_risk_overflow problem."""
    settings = ScheduleSettingsInput()
    blocks = [
        ScheduledBlock(
            id="b_at_risk",
            task_id="t_at_risk",
            title="Late Project",
            start_time=ANCHOR_NOW,
            end_time=ANCHOR_NOW + timedelta(hours=2),
            is_at_risk=True,
        )
    ]
    res = analyze_workload(
        tasks=[],
        schedule=blocks,
        settings=settings,
        now=ANCHOR_NOW,
        horizon_days=3,
    )
    assert any(p.problem_type == "at_risk_overflow" for p in res.problems)


def test_realism_score_gradation():
    """Severe overloads drop realism score significantly into 'critical' or 'overloaded'."""
    settings = ScheduleSettingsInput()
    # 5 impossible tasks
    tasks = [
        TaskInput(
            id=f"t{i}",
            title=f"Impossible Task {i}",
            estimated_duration_minutes=300,
            remaining_duration_minutes=300,
            deadline=ANCHOR_NOW + timedelta(hours=1),
        )
        for i in range(5)
    ]
    res = analyze_workload(
        tasks=tasks,
        schedule=[],
        settings=settings,
        now=ANCHOR_NOW,
        horizon_days=3,
    )
    assert res.realism_score < 50
    assert res.status == "critical"
