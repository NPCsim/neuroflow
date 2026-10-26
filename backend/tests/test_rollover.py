import uuid
from datetime import datetime, timedelta, timezone
import pytest
from freezegun import freeze_time
from fastapi import status

from app.models import UserSettings, Task, FixedEvent, ScheduleBlock, ActivityLog


@freeze_time("2026-10-26 12:00:00")
def test_rollover_marks_past_uncompleted_blocks_missed_and_logs(client, db_session):
    """
    POST /schedule/rollover marks past planned blocks that weren't completed as 'missed',
    logs them to activity_log, increments carry-over counts on their tasks, and
    calls build_schedule to place the remaining work.
    """
    now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=10,
    )
    db_session.add(settings)

    # Task 1: had a planned block in the morning that wasn't completed
    t1 = Task(
        id=str(uuid.uuid4()),
        title="Implement Rollover Logic",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="urgent_important",
        status="scheduled",
        carry_over_count=0,
    )

    # Task 2: had a planned block in the morning that WAS completed
    t2 = Task(
        id=str(uuid.uuid4()),
        title="Morning Triage",
        estimated_duration_minutes=45,
        remaining_duration_minutes=0,
        priority="normal",
        status="completed",
        carry_over_count=0,
    )

    db_session.add_all([t1, t2])
    db_session.commit()

    # Past uncompleted block (09:00 - 10:00)
    past_uncompleted_block = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t1.id,
        title="Implement Rollover Logic",
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=2),
        chunk_index=1,
        total_chunks=1,
        is_completed=False,
        status="planned",
    )

    # Past completed block (10:00 - 10:45)
    past_completed_block = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t2.id,
        title="Morning Triage",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1, minutes=15),
        chunk_index=1,
        total_chunks=1,
        is_completed=True,
        status="completed",
    )

    db_session.add_all([past_uncompleted_block, past_completed_block])
    db_session.commit()

    # Invoke rollover with frozen clock
    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert data["missed_blocks_count"] == 1
    assert data["carried_over_tasks_count"] == 1
    assert data["stuck_tasks_count"] == 0

    # 1. Verify past uncompleted block was marked missed in DB
    refreshed_b1 = db_session.query(ScheduleBlock).filter_by(id=past_uncompleted_block.id).first()
    assert refreshed_b1.status == "missed"
    assert refreshed_b1.is_completed is False

    # 2. Verify completed block remained completed
    refreshed_b2 = db_session.query(ScheduleBlock).filter_by(id=past_completed_block.id).first()
    assert refreshed_b2.status == "completed"
    assert refreshed_b2.is_completed is True

    # 3. Verify logged to activity_log with frozen timestamp
    logs = db_session.query(ActivityLog).all()
    assert len(logs) == 1
    assert logs[0].task_id == t1.id
    assert logs[0].schedule_block_id == past_uncompleted_block.id
    assert logs[0].action == "missed"
    log_time = logs[0].created_at if logs[0].created_at.tzinfo else logs[0].created_at.replace(tzinfo=timezone.utc)
    assert log_time == now

    # 4. Verify task carry_over_count incremented
    refreshed_t1 = db_session.query(Task).filter_by(id=t1.id).first()
    assert refreshed_t1.carry_over_count == 1

    # 5. Verify remaining work was rescheduled from now onwards
    new_blocks = (
        db_session.query(ScheduleBlock)
        .filter(ScheduleBlock.task_id == t1.id, ScheduleBlock.status == "planned")
        .all()
    )
    assert len(new_blocks) >= 1
    for b in new_blocks:
        b_st = b.start_time if b.start_time.tzinfo else b.start_time.replace(tzinfo=timezone.utc)
        assert b_st >= now


@freeze_time("2026-10-26 14:00:00")
def test_rollover_task_carried_over_3_times_flagged_as_stuck(client, db_session):
    """
    If a task has been carried over 3+ times, flag it as 'stuck' in the response.
    """
    now = datetime(2026, 10, 26, 14, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    # Task already carried over twice (carry_over_count=2)
    stuck_task = Task(
        id=str(uuid.uuid4()),
        title="Stubborn Bug Investigation",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="important",
        status="scheduled",
        carry_over_count=2,
    )

    # Normal task with carry_over_count=0
    normal_task = Task(
        id=str(uuid.uuid4()),
        title="Standard Code Review",
        estimated_duration_minutes=30,
        remaining_duration_minutes=30,
        priority="normal",
        status="scheduled",
        carry_over_count=0,
    )

    db_session.add_all([stuck_task, normal_task])
    db_session.commit()

    # Past uncompleted blocks for both
    block_stuck = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=stuck_task.id,
        title="Stubborn Bug Investigation",
        start_time=now - timedelta(hours=4),
        end_time=now - timedelta(hours=3),
        is_completed=False,
        status="planned",
    )
    block_normal = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=normal_task.id,
        title="Standard Code Review",
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=2, minutes=30),
        is_completed=False,
        status="planned",
    )

    db_session.add_all([block_stuck, block_normal])
    db_session.commit()

    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert data["missed_blocks_count"] == 2
    assert data["carried_over_tasks_count"] == 2

    # stuck_task reached carry_over_count=3 -> flagged as stuck
    assert data["stuck_tasks_count"] == 1
    assert len(data["stuck_tasks"]) == 1
    assert data["stuck_tasks"][0]["id"] == stuck_task.id
    assert data["stuck_tasks"][0]["is_stuck"] is True
    assert data["stuck_tasks"][0]["flag"] == "stuck"
    assert data["stuck_tasks"][0]["carry_over_count"] == 3
    assert stuck_task.id in data["stuck_task_ids"]

    # normal_task reached carry_over_count=1 -> not stuck
    assert normal_task.id not in data["stuck_task_ids"]

    # Verify database counts
    refreshed_stuck = db_session.query(Task).filter_by(id=stuck_task.id).first()
    assert refreshed_stuck.carry_over_count == 3

    refreshed_normal = db_session.query(Task).filter_by(id=normal_task.id).first()
    assert refreshed_normal.carry_over_count == 1

    # Verify both blocks logged to activity_log
    logs = db_session.query(ActivityLog).all()
    assert len(logs) == 2
    logged_task_ids = {log.task_id for log in logs}
    assert stuck_task.id in logged_task_ids
    assert normal_task.id in logged_task_ids


def test_rollover_multi_day_progression_with_frozen_clock(client, db_session):
    """
    Simulates consecutive day rollovers using a frozen clock advancing across Day 1, Day 2, and Day 3.
    Verifies carry_over_count increments on each rollover and task becomes flagged as 'stuck' at 3.
    """
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=10,
    )
    db_session.add(settings)

    task = Task(
        id=str(uuid.uuid4()),
        title="Multi-Day Unfinished Epic",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="important",
        status="pending",
        carry_over_count=0,
    )
    db_session.add(task)
    db_session.commit()

    # --- DAY 1: Monday, October 26, 2026 at 17:00 UTC ---
    with freeze_time("2026-10-26 17:00:00"):
        day1_now = datetime(2026, 10, 26, 17, 0, 0, tzinfo=timezone.utc)
        b1 = ScheduleBlock(
            id=str(uuid.uuid4()),
            task_id=task.id,
            title="Multi-Day Unfinished Epic",
            start_time=day1_now - timedelta(hours=3),
            end_time=day1_now - timedelta(hours=2),
            is_completed=False,
            status="planned",
        )
        db_session.add(b1)
        db_session.commit()

        res1 = client.post("/schedule/rollover")
        assert res1.status_code == status.HTTP_200_OK
        d1 = res1.json()
        assert d1["missed_blocks_count"] == 1
        assert d1["stuck_tasks_count"] == 0

        db_session.refresh(task)
        assert task.carry_over_count == 1

        logs = db_session.query(ActivityLog).all()
        assert len(logs) == 1
        log_time = logs[0].created_at if logs[0].created_at.tzinfo else logs[0].created_at.replace(tzinfo=timezone.utc)
        assert log_time == day1_now

    # --- DAY 2: Tuesday, October 27, 2026 at 17:00 UTC ---
    with freeze_time("2026-10-27 17:00:00"):
        day2_now = datetime(2026, 10, 27, 17, 0, 0, tzinfo=timezone.utc)
        # Find scheduled block from day 1 build_schedule, simulate it was missed (left is_completed=False)
        res2 = client.post("/schedule/rollover")
        assert res2.status_code == status.HTTP_200_OK
        d2 = res2.json()
        assert d2["missed_blocks_count"] >= 1
        assert d2["stuck_tasks_count"] == 0

        db_session.refresh(task)
        assert task.carry_over_count == 2

        logs = db_session.query(ActivityLog).all()
        assert len(logs) >= 2

    # --- DAY 3: Wednesday, October 28, 2026 at 17:00 UTC ---
    with freeze_time("2026-10-28 17:00:00"):
        day3_now = datetime(2026, 10, 28, 17, 0, 0, tzinfo=timezone.utc)
        res3 = client.post("/schedule/rollover")
        assert res3.status_code == status.HTTP_200_OK
        d3 = res3.json()
        assert d3["missed_blocks_count"] >= 1

        # Now carry_over_count >= 3 -> MUST be flagged as stuck!
        assert d3["stuck_tasks_count"] == 1
        assert d3["stuck_tasks"][0]["id"] == task.id
        assert d3["stuck_tasks"][0]["carry_over_count"] >= 3
        assert d3["stuck_tasks"][0]["is_stuck"] is True
        assert d3["stuck_tasks"][0]["flag"] == "stuck"
        assert task.id in d3["stuck_task_ids"]

        db_session.refresh(task)
        assert task.carry_over_count >= 3


@freeze_time("2026-10-26 10:00:00")
def test_rollover_future_blocks_not_marked_missed(client, db_session):
    """
    Blocks scheduled for the future should not be marked as missed.
    Only past blocks that weren't completed are marked as missed.
    """
    now = datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    task = Task(
        id=str(uuid.uuid4()),
        title="Future Task",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        status="scheduled",
    )
    db_session.add(task)
    db_session.commit()

    # Block in the future: 14:00 - 15:00 today
    future_block = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=task.id,
        title="Future Task",
        start_time=now + timedelta(hours=4),
        end_time=now + timedelta(hours=5),
        is_completed=False,
        status="planned",
    )
    db_session.add(future_block)
    db_session.commit()

    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["missed_blocks_count"] == 0
    assert data["carried_over_tasks_count"] == 0

    # No activity log created for future block
    logs = db_session.query(ActivityLog).all()
    assert len(logs) == 0

    # Task carry_over_count remains 0
    db_session.refresh(task)
    assert task.carry_over_count == 0


@freeze_time("2026-10-26 11:00:00")
def test_rollover_avoids_fixed_events(client, db_session):
    """
    Verifies that calling build_schedule during rollover properly avoids fixed events.
    """
    now = datetime(2026, 10, 26, 11, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=10,
    )
    db_session.add(settings)

    # Task missed in the morning (09:00 - 10:00)
    task = Task(
        id=str(uuid.uuid4()),
        title="High Priority Proposal",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="urgent_important",
        status="scheduled",
    )
    db_session.add(task)

    # Fixed meeting from 11:30 to 12:30
    fixed = FixedEvent(
        id=str(uuid.uuid4()),
        title="Executive Strategy Sync",
        start_time=now + timedelta(minutes=30),
        end_time=now + timedelta(minutes=90),
        source="calendar",
    )
    db_session.add(fixed)

    missed_block = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=task.id,
        title="High Priority Proposal",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        is_completed=False,
        status="planned",
    )
    db_session.add(missed_block)
    db_session.commit()

    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["missed_blocks_count"] == 1

    # Verify newly placed blocks do not overlap the fixed event (11:30 - 12:30)
    new_blocks = [
        b for b in data["blocks"]
        if b["task_id"] == task.id and b["status"] == "planned"
    ]
    assert len(new_blocks) >= 1
    fixed_start = fixed.start_time if fixed.start_time.tzinfo else fixed.start_time.replace(tzinfo=timezone.utc)
    fixed_end = fixed.end_time if fixed.end_time.tzinfo else fixed.end_time.replace(tzinfo=timezone.utc)
    for b in new_blocks:
        b_start = datetime.fromisoformat(b["start_time"])
        b_end = datetime.fromisoformat(b["end_time"])
        if b_start.tzinfo is None:
            b_start = b_start.replace(tzinfo=timezone.utc)
        if b_end.tzinfo is None:
            b_end = b_end.replace(tzinfo=timezone.utc)
        # Must not overlap with 11:30 - 12:30
        assert b_end <= fixed_start or b_start >= fixed_end


@freeze_time("2026-10-26 15:00:00")
def test_rollover_with_explicit_body_parameters(client, db_session):
    """
    Verifies that POST /schedule/rollover accepts horizon_days, explicit now / current_time in request body.
    """
    ref_time = datetime(2026, 10, 26, 15, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    task = Task(
        id=str(uuid.uuid4()),
        title="Custom Parameter Task",
        estimated_duration_minutes=45,
        remaining_duration_minutes=45,
        status="scheduled",
    )
    db_session.add(task)

    past_block = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=task.id,
        title="Custom Parameter Task",
        start_time=ref_time - timedelta(hours=2),
        end_time=ref_time - timedelta(hours=1),
        is_completed=False,
        status="planned",
    )
    db_session.add(past_block)
    db_session.commit()

    response = client.post(
        "/schedule/rollover",
        json={"horizon_days": 3, "current_time": ref_time.isoformat()},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert data["missed_blocks_count"] == 1
    assert data["carried_over_tasks_count"] == 1
    assert len(data["activity_logs"]) == 1


@freeze_time("2026-10-26 16:00:00")
def test_rollover_multiple_stuck_tasks_flagged(client, db_session):
    """
    Verifies that if multiple tasks have been carried over 3+ times (e.g. 3 and 4),
    both are flagged as 'stuck' in stuck_tasks, stuck_task_ids, and tasks list.
    """
    now = datetime(2026, 10, 26, 16, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    t1 = Task(
        id=str(uuid.uuid4()),
        title="Stuck Task A",
        estimated_duration_minutes=30,
        remaining_duration_minutes=30,
        carry_over_count=2,  # Will reach 3
        status="scheduled",
    )
    t2 = Task(
        id=str(uuid.uuid4()),
        title="Stuck Task B",
        estimated_duration_minutes=30,
        remaining_duration_minutes=30,
        carry_over_count=3,  # Will reach 4
        status="scheduled",
    )
    t3 = Task(
        id=str(uuid.uuid4()),
        title="Normal Task C",
        estimated_duration_minutes=30,
        remaining_duration_minutes=30,
        carry_over_count=0,  # Will reach 1
        status="scheduled",
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    b1 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t1.id,
        title="Stuck Task A",
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=2, minutes=30),
        is_completed=False,
    )
    b2 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t2.id,
        title="Stuck Task B",
        start_time=now - timedelta(hours=2, minutes=30),
        end_time=now - timedelta(hours=2),
        is_completed=False,
    )
    b3 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t3.id,
        title="Normal Task C",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1, minutes=30),
        is_completed=False,
    )
    db_session.add_all([b1, b2, b3])
    db_session.commit()

    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["missed_blocks_count"] == 3
    assert data["carried_over_tasks_count"] == 3
    assert data["stuck_tasks_count"] == 2

    stuck_ids = set(data["stuck_task_ids"])
    assert t1.id in stuck_ids
    assert t2.id in stuck_ids
    assert t3.id not in stuck_ids

    # Check tasks list for flags
    task_map = {t["id"]: t for t in data["tasks"]}
    assert task_map[t1.id]["is_stuck"] is True
    assert task_map[t1.id]["flag"] == "stuck"
    assert task_map[t2.id]["is_stuck"] is True
    assert task_map[t2.id]["flag"] == "stuck"
    assert task_map[t3.id]["is_stuck"] is False
    assert task_map[t3.id]["flag"] is None


@freeze_time("2026-10-26 12:00:00")
def test_rollover_no_missed_blocks_is_clean(client, db_session):
    """
    When no blocks were missed, rollover succeeds with 0 missed blocks and still ensures
    clean scheduling of pending tasks.
    """
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)
    db_session.commit()

    response = client.post("/schedule/rollover")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert data["missed_blocks_count"] == 0
    assert data["carried_over_tasks_count"] == 0
    assert data["stuck_tasks_count"] == 0
    assert len(data["activity_logs"]) == 0
