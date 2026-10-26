from __future__ import annotations

import uuid
from datetime import datetime, date, time, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from google.genai import types

from app.models import Task, ScheduleBlock, FixedEvent, PlanProposal, UserSettings
from app.services.agent_tools import (
    execute_agent_tool,
    service_get_plan,
    service_move_task,
    service_split_task,
    service_defer_task,
    service_set_priority,
    service_add_task,
    service_mark_done,
    service_reduce_available_time,
    service_rebuild_schedule,
)


@pytest.fixture
def base_schedule_setup(db_session):
    """Sets up standard user settings, 3 tasks, and baseline schedule blocks."""
    fixed_now = datetime(2026, 10, 26, 9, 0, 0, tzinfo=timezone.utc)  # Monday morning 9 AM

    settings = UserSettings(
        timezone="UTC",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=10,
        min_chunk_minutes=30,
        max_chunk_minutes=120,
    )
    db_session.add(settings)

    t1 = Task(
        id=str(uuid.uuid4()),
        title="Weekly Status Report",
        estimated_duration_minutes=120,
        remaining_duration_minutes=120,
        priority="normal",
        deadline=fixed_now + timedelta(days=2),
        status="scheduled",
    )
    t2 = Task(
        id=str(uuid.uuid4()),
        title="DBMS Exam Prep",
        estimated_duration_minutes=180,
        remaining_duration_minutes=180,
        priority="important",
        deadline=fixed_now + timedelta(days=4),
        status="scheduled",
    )
    t3 = Task(
        id=str(uuid.uuid4()),
        title="Inbox Zero & Admin",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="low",
        deadline=fixed_now + timedelta(days=1),
        status="scheduled",
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # Initial blocks placed for today
    b1 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t1.id,
        title=t1.title,
        start_time=fixed_now,
        end_time=fixed_now + timedelta(minutes=120),
        status="planned",
    )
    b2 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t2.id,
        title=t2.title,
        start_time=fixed_now + timedelta(minutes=130),
        end_time=fixed_now + timedelta(minutes=310),
        status="planned",
    )
    b3 = ScheduleBlock(
        id=str(uuid.uuid4()),
        task_id=t3.id,
        title=t3.title,
        start_time=fixed_now + timedelta(minutes=320),
        end_time=fixed_now + timedelta(minutes=380),
        status="planned",
    )
    db_session.add_all([b1, b2, b3])
    db_session.commit()

    return {
        "fixed_now": fixed_now,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "blocks": [b1, b2, b3],
    }


def test_agent_command_reduced_capacity_staging_without_committing(client, db_session, base_schedule_setup):
    """
    User says: 'I only have 3 hours today'
    Agent calls:
      Step 1: reduce_available_time(date="today", minutes_lost=300)
      Step 2: rebuild_schedule()
      Step 3: summary text
    Verifies that:
      - Backend stages changes in a transaction WITHOUT committing to main tables.
      - Computes plan diff (moved, deferred, dropped, at-risk).
      - Returns {summary, diff, snapshot_id}.
    """
    fixed_now = base_schedule_setup["fixed_now"]

    # Scripted LLM responses
    resp1 = MagicMock()
    resp1.function_calls = [
        types.FunctionCall(name="reduce_available_time", args={"date": "today", "minutes_lost": 300})
    ]
    resp1.text = None

    resp2 = MagicMock()
    resp2.function_calls = [
        types.FunctionCall(name="rebuild_schedule", args={"horizon_days": 7})
    ]
    resp2.text = None

    resp3 = MagicMock()
    resp3.function_calls = []
    resp3.text = "Reduced today's capacity by 5 hours (300 minutes). Staged overflow tasks to subsequent days."

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [resp1, resp2, resp3]

    with patch("app.services.agent_service.genai.Client", return_value=mock_client):
        res = client.post(
            "/agent/command",
            json={
                "message": "I only have 3 hours today",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert "summary" in data
    assert "diff" in data
    assert "snapshot_id" in data
    assert data["status"] == "staged"
    assert "Reduced today's capacity" in data["summary"]

    diff = data["diff"]
    assert "moved" in diff
    assert "deferred" in diff
    assert "dropped" in diff
    assert "at_risk" in diff
    assert "at-risk" in diff

    snapshot_id = data["snapshot_id"]

    # CRITICAL: Verify staging did NOT commit changes to the active database yet
    # Baseline had 3 planned blocks today; none of the active blocks should be modified or deleted yet
    active_blocks = db_session.query(ScheduleBlock).all()
    assert len(active_blocks) == 3

    # Verify a PlanProposal record was saved in draft_pending status
    proposal = db_session.query(PlanProposal).filter_by(id=snapshot_id).first()
    assert proposal is not None
    assert proposal.status == "draft_pending"
    assert proposal.summary is not None
    assert "diff" in proposal.diff_payload
    assert "staged_state" in proposal.diff_payload


def test_agent_command_defer_and_priority_staging(client, db_session, base_schedule_setup):
    """
    User says: 'push the report to Friday and make the exam prep top priority'
    Agent calls:
      Step 1: defer_task(report, Friday) and set_priority(exam, 5)
      Step 2: rebuild_schedule()
      Step 3: summary text
    Verifies diff categorizes deferred and moved tasks properly.
    """
    fixed_now = base_schedule_setup["fixed_now"]
    t1 = base_schedule_setup["t1"]
    t2 = base_schedule_setup["t2"]

    resp1 = MagicMock()
    resp1.function_calls = [
        types.FunctionCall(name="defer_task", args={"task_id": t1.id, "new_deadline": "Friday"}),
        types.FunctionCall(name="set_priority", args={"task_id": t2.id, "importance": 5}),
    ]
    resp1.text = None

    resp2 = MagicMock()
    resp2.function_calls = [
        types.FunctionCall(name="rebuild_schedule", args={})
    ]
    resp2.text = None

    resp3 = MagicMock()
    resp3.function_calls = []
    resp3.text = "Deferred Weekly Status Report to Friday and promoted DBMS Exam Prep to top priority (urgent_important)."

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [resp1, resp2, resp3]

    with patch("app.services.agent_service.genai.Client", return_value=mock_client):
        res = client.post(
            "/agent/command",
            json={
                "command": "push the report to Friday and make the exam prep top priority",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    diff = data["diff"]

    assert len(diff["deferred"]) >= 1
    deferred_titles = [d["title"] for d in diff["deferred"]]
    assert t1.title in deferred_titles

    # Prioritized task was moved or placed earlier
    assert len(diff["moved"]) >= 1

    # Database still uncommitted before apply
    t2_current = db_session.query(Task).filter_by(id=t2.id).first()
    assert t2_current.priority == "important"  # Not changed to urgent_important in active DB yet!


def test_agent_safety_cannot_delete_tasks(client, db_session, base_schedule_setup):
    """
    Safety mandate: The agent cannot delete tasks, only defer or flag them.
    If the LLM calls any delete tool, it is intercepted and rejected with an error.
    """
    t1 = base_schedule_setup["t1"]

    # Test direct execution safety guard
    safety_result = execute_agent_tool("delete_task", {"task_id": t1.id}, db_session)
    assert "error" in safety_result
    assert "cannot delete tasks" in safety_result["error"].lower()

    # Verify task still exists in DB
    assert db_session.query(Task).filter_by(id=t1.id).first() is not None

    # Test remove_task alias
    safety_result_2 = execute_agent_tool("remove_task", {"task_id": t1.id}, db_session)
    assert "error" in safety_result_2


def test_agent_apply_and_undo_lifecycle(client, db_session, base_schedule_setup):
    """
    Tests the complete lifecycle:
      1. POST /agent/command -> stages proposal (snapshot_id)
      2. POST /agent/apply/{snapshot_id} -> commits staged proposal to DB
      3. POST /agent/undo/{snapshot_id} -> reverts DB back to snapshot_before
    """
    fixed_now = base_schedule_setup["fixed_now"]
    t1 = base_schedule_setup["t1"]
    t2 = base_schedule_setup["t2"]

    # 1. Stage changes: split t1, defer t2, mark t3 done
    t3 = base_schedule_setup["t3"]
    resp1 = MagicMock()
    resp1.function_calls = [
        types.FunctionCall(name="split_task", args={"task_id": t1.id, "parts": 2}),
        types.FunctionCall(name="defer_task", args={"task_id": t2.id, "new_deadline": "2026-10-31T17:00:00Z"}),
        types.FunctionCall(name="mark_done", args={"task_id": t3.id}),
    ]
    resp1.text = None

    resp2 = MagicMock()
    resp2.function_calls = []
    resp2.text = "Split Report into 2 chunks, deferred Exam Prep to Oct 31, and completed Inbox Zero."

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [resp1, resp2]

    with patch("app.services.agent_service.genai.Client", return_value=mock_client):
        stage_res = client.post(
            "/agent/command",
            json={"message": "Split report into 2, push exam prep to Oct 31, and mark admin done"},
        )
    assert stage_res.status_code == status.HTTP_200_OK
    snapshot_id = stage_res.json()["snapshot_id"]

    # Verify DB still has old state before apply
    t3_before = db_session.query(Task).filter_by(id=t3.id).first()
    assert t3_before.status != "completed"

    # 2. Apply snapshot
    apply_res = client.post(f"/agent/apply/{snapshot_id}")
    assert apply_res.status_code == status.HTTP_200_OK
    apply_data = apply_res.json()
    assert apply_data["status"] == "applied"
    assert apply_data["snapshot_id"] == snapshot_id

    # Verify committed in active database
    db_session.expire_all()
    t3_applied = db_session.query(Task).filter_by(id=t3.id).first()
    assert t3_applied.status == "completed"

    t1_applied = db_session.query(Task).filter_by(id=t1.id).first()
    assert t1_applied.is_splittable is True
    assert t1_applied.min_chunk_minutes == 60

    # 3. Undo snapshot (revert)
    undo_res = client.post(f"/agent/undo/{snapshot_id}")
    assert undo_res.status_code == status.HTTP_200_OK
    undo_data = undo_res.json()
    assert undo_data["status"] == "reverted"
    assert undo_data["previous_status"] == "approved"

    # Verify reverted in active database
    db_session.expire_all()
    t3_reverted = db_session.query(Task).filter_by(id=t3.id).first()
    assert t3_reverted.status == "scheduled"  # Restored to baseline status


def test_agent_undo_draft_discards_without_touching_db(client, db_session, base_schedule_setup):
    """
    Calling POST /agent/undo/{snapshot_id} on a draft_pending proposal marks it rejected
    and leaves the active schedule intact.
    """
    fixed_now = base_schedule_setup["fixed_now"]

    resp1 = MagicMock()
    resp1.function_calls = [
        types.FunctionCall(name="add_task", args={"title": "Temporary Spike", "est_minutes": 45, "importance": 4})
    ]
    resp1.text = None

    resp2 = MagicMock()
    resp2.function_calls = []
    resp2.text = "Added Temporary Spike task."

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [resp1, resp2]

    with patch("app.services.agent_service.genai.Client", return_value=mock_client):
        stage_res = client.post("/agent/command", json={"message": "Add a temporary spike task"})
    assert stage_res.status_code == status.HTTP_200_OK
    snapshot_id = stage_res.json()["snapshot_id"]

    # Undo the draft
    undo_res = client.post(f"/agent/undo/{snapshot_id}")
    assert undo_res.status_code == status.HTTP_200_OK
    assert undo_res.json()["status"] == "rejected"
    assert undo_res.json()["previous_status"] == "draft_pending"

    # Temporary Spike task should not exist in active database
    assert db_session.query(Task).filter_by(title="Temporary Spike").first() is None


def test_agent_max_steps_loop_termination(client, db_session, base_schedule_setup):
    """
    Verifies that the agent loop stops gracefully after max 6 steps even if the LLM
    keeps returning function calls.
    """
    fixed_now = base_schedule_setup["fixed_now"]

    # Return function call indefinitely
    infinite_tool_response = MagicMock()
    infinite_tool_response.function_calls = [
        types.FunctionCall(name="get_plan", args={"range": "today"})
    ]
    infinite_tool_response.text = None

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = infinite_tool_response

    with patch("app.services.agent_service.genai.Client", return_value=mock_client):
        res = client.post("/agent/command", json={"message": "Keep planning"})

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["steps_executed"] == 6
    assert data["status"] == "staged"
    assert "snapshot_id" in data


def test_individual_service_tools_coverage(db_session, base_schedule_setup):
    """
    Direct unit tests ensuring each of the 9 service functions works properly.
    """
    fixed_now = base_schedule_setup["fixed_now"]
    t1 = base_schedule_setup["t1"]

    # 1. get_plan
    plan = service_get_plan(db_session, "today", fixed_now)
    assert plan["scheduled_blocks_count"] == 3
    assert plan["active_tasks_count"] == 3

    # 2. move_task
    move_res = service_move_task(db_session, t1.id, "2026-10-27T10:00:00Z", fixed_now)
    assert move_res["status"] == "success"

    # 3. split_task
    split_res = service_split_task(db_session, t1.id, 3)
    assert split_res["status"] == "success"
    assert split_res["parts"] == 3

    # 4. defer_task
    defer_res = service_defer_task(db_session, t1.id, "2026-11-05T17:00:00Z", fixed_now)
    assert defer_res["status"] == "success"
    assert "2026-11-05" in defer_res["new_deadline"]

    # 5. set_priority
    prio_res = service_set_priority(db_session, t1.id, 5)
    assert prio_res["status"] == "success"
    assert prio_res["priority"] == "urgent_important"

    # 6. add_task
    add_res = service_add_task(
        db_session,
        title="New Research Task",
        est_minutes=90,
        importance=4,
        deadline="2026-10-30T17:00:00Z",
        category="research",
        reference_time=fixed_now,
    )
    assert add_res["status"] == "success"
    assert add_res["title"] == "New Research Task"

    # 7. mark_done
    done_res = service_mark_done(db_session, t1.id)
    assert done_res["status"] == "success"
    assert done_res["task_status"] == "completed"

    # 8. reduce_available_time
    reduce_res = service_reduce_available_time(db_session, "today", 180, fixed_now)
    assert reduce_res["status"] == "success"
    assert reduce_res["minutes_lost"] == 180

    # 9. rebuild_schedule
    sched_res = service_rebuild_schedule(db_session, start=fixed_now, horizon_days=7)
    assert sched_res["status"] == "success"
    assert "scheduled_blocks_count" in sched_res


def test_post_agent_undo_endpoint(client, db_session, base_schedule_setup):
    """POST /agent/undo without snapshot_id reverts the latest applied proposal."""
    proposal = PlanProposal(
        id=str(uuid.uuid4()),
        summary="Test proposal to undo",
        diff_payload={"diff": {}, "staged_state": {}},
        snapshot_before={"tasks": [], "blocks": [], "fixed_events": []},
        status="applied",
    )
    db_session.add(proposal)
    db_session.commit()

    res = client.post("/agent/undo")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "reverted"
    assert data["snapshot_id"] == proposal.id

