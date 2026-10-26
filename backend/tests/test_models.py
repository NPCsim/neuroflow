import uuid
from datetime import datetime, timezone, timedelta
from app.models import (
    UserSettings,
    Goal,
    Task,
    FixedEvent,
    ScheduleBlock,
    PlanProposal,
    ChatMessage,
)


def test_user_settings_creation(db_session):
    settings = UserSettings(
        timezone="America/New_York",
        work_start_time="09:00",
        work_end_time="17:00",
        work_days=[0, 1, 2, 3, 4],
        buffer_minutes=15,
    )
    db_session.add(settings)
    db_session.commit()

    saved = db_session.query(UserSettings).filter_by(id=settings.id).first()
    assert saved is not None
    assert saved.timezone == "America/New_York"
    assert saved.buffer_minutes == 15
    assert saved.work_days == [0, 1, 2, 3, 4]


def test_goal_and_task_relationship(db_session):
    goal = Goal(
        title="Complete Hackathon MVP",
        description="Ship autonomous scheduling agent",
    )
    db_session.add(goal)
    db_session.commit()

    task1 = Task(
        goal_id=goal.id,
        title="Setup Database",
        estimated_duration_minutes=60,
        remaining_duration_minutes=60,
        priority="urgent_important",
    )
    task2 = Task(
        goal_id=goal.id,
        title="Setup Frontend",
        estimated_duration_minutes=90,
        remaining_duration_minutes=90,
        priority="important",
    )
    db_session.add_all([task1, task2])
    db_session.commit()

    fetched_goal = db_session.query(Goal).filter_by(id=goal.id).first()
    assert len(fetched_goal.tasks) == 2
    assert fetched_goal.tasks[0].goal.title == "Complete Hackathon MVP"


def test_schedule_block_and_plan_proposal(db_session):
    now = datetime.now(timezone.utc)
    task = Task(title="Important Review", estimated_duration_minutes=30)
    db_session.add(task)
    db_session.commit()

    block = ScheduleBlock(
        task_id=task.id,
        title="Important Review - Chunk 1",
        start_time=now,
        end_time=now + timedelta(minutes=30),
        chunk_index=1,
        total_chunks=1,
    )
    db_session.add(block)

    proposal = PlanProposal(
        summary="Auto-schedule Important Review",
        diff_payload={"added_blocks": [{"title": "Important Review"}]},
        snapshot_before={"blocks": []},
    )
    db_session.add(proposal)
    db_session.commit()

    chat = ChatMessage(
        sender="agent",
        content="Proposed schedule for Important Review.",
        proposal_id=proposal.id,
    )
    db_session.add(chat)
    db_session.commit()

    assert block.task.title == "Important Review"
    assert len(proposal.messages) == 1
    assert proposal.messages[0].sender == "agent"


def test_activity_log_creation_and_task_relationship(db_session):
    from app.models import ActivityLog

    task = Task(title="Logged Task", estimated_duration_minutes=60, carry_over_count=1)
    db_session.add(task)
    db_session.commit()

    block = ScheduleBlock(
        task_id=task.id,
        title="Logged Block",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=60),
        status="missed",
    )
    db_session.add(block)
    db_session.commit()

    log = ActivityLog(
        task_id=task.id,
        schedule_block_id=block.id,
        action="missed",
        title="Logged Block",
        description="Block marked missed",
    )
    db_session.add(log)
    db_session.commit()

    fetched = db_session.query(ActivityLog).filter_by(id=log.id).first()
    assert fetched is not None
    assert fetched.action == "missed"
    assert fetched.task.title == "Logged Task"
    assert fetched.schedule_block.title == "Logged Block"
    assert len(task.activity_logs) == 1
