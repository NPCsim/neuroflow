import uuid
from datetime import datetime, timedelta, timezone
from fastapi import status
from app.models import UserSettings, Task, FixedEvent, ScheduleBlock


def test_get_workload_endpoint(client, db_session):
    """GET /workload returns valid workload analysis with per-day load percentage and realism score."""
    now = datetime.now(timezone.utc)
    settings = UserSettings(
        timezone="America/New_York",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    task = Task(
        title="Analyze Performance Metrics",
        estimated_duration_minutes=120,
        remaining_duration_minutes=120,
        priority="important",
        status="pending",
    )
    db_session.add(task)
    db_session.commit()

    response = client.get("/workload?horizon_days=5")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "realism_score" in data
    assert 0 <= data["realism_score"] <= 100
    assert "status" in data
    assert "daily_loads" in data
    assert len(data["daily_loads"]) == 5
    assert "problems" in data


def test_post_schedule_rebuild_endpoint(client, db_session):
    """POST /schedule/rebuild triggers scheduler, commits blocks to DB, and returns updated workload."""
    now = datetime.now(timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=10,
    )
    db_session.add(settings)

    t1 = Task(
        id=str(uuid.uuid4()),
        title="Task 1",
        estimated_duration_minutes=90,
        remaining_duration_minutes=90,
        status="pending",
    )
    t2 = Task(
        id=str(uuid.uuid4()),
        title="Task 2",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        status="pending",
    )
    event = FixedEvent(
        id=str(uuid.uuid4()),
        title="Daily Standup",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=1, minutes=30),
    )
    db_session.add_all([t1, t2, event])
    db_session.commit()

    response = client.post(
        "/schedule/rebuild",
        json={"horizon_days": 3, "start": now.isoformat()},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert data["scheduled_blocks_count"] >= 2
    assert len(data["blocks"]) >= 2
    assert "workload_analysis" in data
    assert "realism_score" in data["workload_analysis"]

    # Verify blocks are persisted in the database
    db_blocks = db_session.query(ScheduleBlock).all()
    assert len(db_blocks) >= 2


def test_get_schedule_overview_endpoint(client, db_session):
    """GET /schedule returns full schedule overview with blocks, fixed events, goals, and workload."""
    now = datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    task = Task(
        title="Schedule Test Task",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        status="scheduled",
    )
    db_session.add(task)
    db_session.commit()

    block = ScheduleBlock(
        task_id=task.id,
        title="Schedule Test Task",
        start_time=now,
        end_time=now + timedelta(minutes=60),
        status="planned",
    )
    event = FixedEvent(
        title="Test Fixed Sync",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=2, minutes=30),
    )
    db_session.add_all([block, event])
    db_session.commit()

    response = client.get("/schedule?horizon_days=5")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "success"
    assert "blocks" in data
    assert len(data["blocks"]) >= 1
    assert "fixed_events" in data
    assert len(data["fixed_events"]) >= 1
    assert "workload" in data
    assert "realism_score" in data["workload"]


def test_schedule_block_status_endpoint(client, db_session):
    """POST /schedule/block/{block_id}/status marks block completed/missed/planned and updates task."""
    task = Task(
        title="Status Update Task",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        status="scheduled",
    )
    db_session.add(task)
    db_session.commit()

    block = ScheduleBlock(
        task_id=task.id,
        title="Status Update Task",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=60),
        status="planned",
    )
    db_session.add(block)
    db_session.commit()

    # 1. Mark completed
    resp1 = client.post(f"/schedule/block/{block.id}/status", json={"status": "completed"})
    assert resp1.status_code == status.HTTP_200_OK
    assert resp1.json()["block_status"] == "completed"
    assert resp1.json()["is_completed"] is True

    db_session.refresh(block)
    db_session.refresh(task)
    assert block.is_completed is True
    assert task.status == "completed"

    # 2. Mark missed
    resp2 = client.post(f"/schedule/block/{block.id}/status", json={"status": "missed"})
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["block_status"] == "missed"

    # 3. Invalid status returns 400
    resp3 = client.post(f"/schedule/block/{block.id}/status", json={"status": "invalid_status"})
    assert resp3.status_code == status.HTTP_400_BAD_REQUEST


def test_schedule_reschedule_with_conflict_revalidation(client, db_session):
    """POST /schedule/reschedule re-validates against fixed events, other blocks, and working hours."""
    # Monday Oct 26, 2026: 09:00 - 17:00 UTC
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    db_session.add(settings)

    block1 = ScheduleBlock(
        title="Block A",
        start_time=datetime(2026, 10, 26, 9, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
        status="planned",
    )
    block2 = ScheduleBlock(
        title="Block B",
        start_time=datetime(2026, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
        status="planned",
    )
    fixed = FixedEvent(
        title="Mandatory All Hands",
        start_time=datetime(2026, 10, 26, 14, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 26, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([block1, block2, fixed])
    db_session.commit()

    # 1. Valid reschedule to open afternoon window 11:30 - 12:30
    valid_resp = client.post(
        "/schedule/reschedule",
        json={
            "block_id": block1.id,
            "new_start": datetime(2026, 10, 26, 11, 30, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert valid_resp.status_code == status.HTTP_200_OK
    assert valid_resp.json()["status"] == "success"

    # 2. Conflict with Fixed Event -> Rejected with 400
    conflict_fixed = client.post(
        "/schedule/reschedule",
        json={
            "block_id": block1.id,
            "new_start": datetime(2026, 10, 26, 14, 15, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert conflict_fixed.status_code == status.HTTP_400_BAD_REQUEST
    assert "Mandatory All Hands" in conflict_fixed.json()["detail"]

    # 3. Conflict with other block -> Rejected with 400
    conflict_block = client.post(
        "/schedule/reschedule",
        json={
            "block_id": block1.id,
            "new_start": datetime(2026, 10, 26, 10, 15, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert conflict_block.status_code == status.HTTP_400_BAD_REQUEST
    assert "Block B" in conflict_block.json()["detail"]

    # 4. Outside working hours (e.g. 18:00 UTC when day ends at 17:00) -> Rejected with 400
    outside_hours = client.post(
        "/schedule/reschedule",
        json={
            "block_id": block1.id,
            "new_start": datetime(2026, 10, 26, 18, 0, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert outside_hours.status_code == status.HTTP_400_BAD_REQUEST
    assert "outside working hours" in outside_hours.json()["detail"]


def test_apply_workload_remedy_endpoint(client, db_session):
    """POST /workload/remedy/apply applies action and rebuilds schedule."""
    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
    )
    task = Task(
        title="At Risk Task",
        estimated_duration_minutes=180,
        remaining_duration_minutes=180,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status="pending",
    )
    db_session.add_all([settings, task])
    db_session.commit()

    resp = client.post(
        "/workload/remedy/apply",
        json={
            "action": "reduce_scope",
            "task_id": task.id,
            "parameters": {"reduction_percentage": 50},
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "success"
    assert "realism_score" in resp.json()

    db_session.refresh(task)
    assert task.estimated_duration_minutes == 90

