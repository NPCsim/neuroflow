import uuid
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal, Base, engine
from app.models import (
    UserSettings,
    Goal,
    Task,
    FixedEvent,
    ScheduleBlock,
    PlanProposal,
    ChatMessage,
    ActivityLog,
)


from typing import Optional
from sqlalchemy.orm import Session

FIXED_DEMO_NOW = datetime(2026, 10, 26, 9, 0, 0, tzinfo=timezone.utc)


def seed_database(fixed_now: Optional[datetime] = None, db: Optional[Session] = None):
    """Seed a realistic demo workspace with goals, tasks, fixed events, and past activity."""
    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Clear existing data to allow clean re-seeding
        db.query(ActivityLog).delete()
        db.query(ChatMessage).delete()
        db.query(PlanProposal).delete()
        db.query(ScheduleBlock).delete()
        db.query(Task).delete()
        db.query(Goal).delete()
        db.query(FixedEvent).delete()
        db.query(UserSettings).delete()
        db.commit()

        now = fixed_now or FIXED_DEMO_NOW
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. User Settings
        settings = UserSettings(
            id=str(uuid.uuid4()),
            timezone="America/New_York",
            work_start_time="09:00",
            work_end_time="17:00",
            work_days=[0, 1, 2, 3, 4],  # Mon - Fri
            buffer_minutes=10,
            min_chunk_minutes=30,
            max_chunk_minutes=120,
        )
        db.add(settings)

        # 2. Goals
        goal_mvp = Goal(
            id=str(uuid.uuid4()),
            title="Launch NeuroFlow MVP",
            description="Complete core autonomous scheduler agent, visual diff engine, and interactive dashboard for the hackathon.",
            target_date=now + timedelta(days=5),
            status="in_progress",
        )
        goal_pitch = Goal(
            id=str(uuid.uuid4()),
            title="Customer Discovery & Pitch",
            description="Interview 10 beta testers, build pitch deck, and rehearse demo presentation for judges.",
            target_date=now + timedelta(days=7),
            status="in_progress",
        )
        goal_platform = Goal(
            id=str(uuid.uuid4()),
            title="Core Platform Resilience",
            description="Achieve 100% test coverage on scheduler non-overlap guarantees and mock all LLM endpoints.",
            target_date=now + timedelta(days=4),
            status="in_progress",
        )
        db.add_all([goal_mvp, goal_pitch, goal_platform])
        db.flush()

        # 3. Tasks (including completed, missed/unfinished, and scheduled)
        tasks = [
            # MVP Tasks
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_mvp.id,
                title="Design Deterministic Interval Scheduler",
                description="Implement interval subtraction for fixed events and priority queue packing.",
                estimated_duration_minutes=90,
                remaining_duration_minutes=0,
                priority="urgent_important",
                deadline=now - timedelta(days=1),
                is_splittable=True,
                status="completed",
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_mvp.id,
                title="Implement Staged Plan Diff Engine",
                description="Calculate before/after diffs and create rollback snapshot payloads.",
                estimated_duration_minutes=120,
                remaining_duration_minutes=120,
                priority="urgent_important",
                deadline=now - timedelta(hours=3),
                is_splittable=True,
                carry_over_count=2,
                status="missed",  # Missed / unfinished task!
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_mvp.id,
                title="Build LLM Tool Calling Agent",
                description="Connect OpenAI/Claude function calling to propose schedule adjustments.",
                estimated_duration_minutes=90,
                remaining_duration_minutes=90,
                priority="urgent_important",
                deadline=now + timedelta(days=1),
                is_splittable=True,
                status="scheduled",
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_mvp.id,
                title="Record & Edit 3-Minute Demo Video",
                description="Showcase live goal decomposition, schedule diff approval, and undo.",
                estimated_duration_minutes=60,
                remaining_duration_minutes=60,
                priority="normal",
                deadline=now + timedelta(days=3),
                is_splittable=False,
                status="pending",
            ),
            # Pitch Tasks
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_pitch.id,
                title="Draft 1-Page Product Vision Memo",
                description="Summarize problem statement, market differentiation, and tech stack.",
                estimated_duration_minutes=45,
                remaining_duration_minutes=0,
                priority="important",
                deadline=now - timedelta(days=2),
                is_splittable=False,
                status="completed",
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_pitch.id,
                title="Synthesize Beta Feedback on Schedule Drift",
                description="Review survey responses from first 5 user test sessions.",
                estimated_duration_minutes=60,
                remaining_duration_minutes=60,
                priority="normal",
                deadline=now - timedelta(hours=6),
                is_splittable=True,
                status="missed",  # Another missed task!
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_pitch.id,
                title="Prepare Slide Deck for Hackathon Judges",
                description="10 slides: problem, agentic architecture, deterministic scheduler, demo, vision.",
                estimated_duration_minutes=90,
                remaining_duration_minutes=90,
                priority="urgent_important",
                deadline=now + timedelta(days=2),
                is_splittable=True,
                status="scheduled",
            ),
            # Platform Tasks
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_platform.id,
                title="Setup Pytest Test Suite & Mocks",
                description="Add unit tests for health check, models, and mock LLM calls.",
                estimated_duration_minutes=45,
                remaining_duration_minutes=0,
                priority="important",
                deadline=now - timedelta(days=1),
                is_splittable=False,
                status="completed",
            ),
            Task(
                id=str(uuid.uuid4()),
                goal_id=goal_platform.id,
                title="Configure Timezone UTC Normalization",
                description="Ensure database stores pure UTC and frontend translates to user timezone.",
                estimated_duration_minutes=30,
                remaining_duration_minutes=0,
                priority="normal",
                deadline=now - timedelta(days=1),
                is_splittable=False,
                status="completed",
            ),
        ]
        db.add_all(tasks)
        db.flush()

        task_dict = {t.title: t for t in tasks}

        # 4. Fixed Events (e.g. daily standups, mentor calls, meetings)
        fixed_events = [
            FixedEvent(
                id=str(uuid.uuid4()),
                title="Team Daily Standup",
                start_time=today_start + timedelta(hours=14),  # 10:00 AM EDT
                end_time=today_start + timedelta(hours=14, minutes=30),
                source="manual",
            ),
            FixedEvent(
                id=str(uuid.uuid4()),
                title="Mentor Office Hours",
                start_time=today_start + timedelta(days=1, hours=19),  # 3:00 PM EDT tomorrow
                end_time=today_start + timedelta(days=1, hours=20),
                source="manual",
            ),
            FixedEvent(
                id=str(uuid.uuid4()),
                title="Sponsor Workshop: Agentic AI",
                start_time=today_start + timedelta(days=2, hours=17),
                end_time=today_start + timedelta(days=2, hours=18, minutes=30),
                source="ics_import",
            ),
        ]
        db.add_all(fixed_events)

        # 5. Schedule Blocks (Past completed blocks + planned blocks)
        blocks = [
            # Yesterday's completed blocks
            ScheduleBlock(
                id=str(uuid.uuid4()),
                task_id=task_dict["Design Deterministic Interval Scheduler"].id,
                title="Design Deterministic Interval Scheduler",
                start_time=today_start - timedelta(days=1, hours=-14),  # 10:00 AM EDT yesterday
                end_time=today_start - timedelta(days=1, hours=-15, minutes=-30),
                chunk_index=1,
                total_chunks=1,
                is_completed=True,
            ),
            ScheduleBlock(
                id=str(uuid.uuid4()),
                task_id=task_dict["Draft 1-Page Product Vision Memo"].id,
                title="Draft 1-Page Product Vision Memo",
                start_time=today_start - timedelta(days=1, hours=-16),
                end_time=today_start - timedelta(days=1, hours=-16, minutes=-45),
                chunk_index=1,
                total_chunks=1,
                is_completed=True,
            ),
            # Today's scheduled block
            ScheduleBlock(
                id=str(uuid.uuid4()),
                task_id=task_dict["Build LLM Tool Calling Agent"].id,
                title="Build LLM Tool Calling Agent (Part 1/2)",
                start_time=today_start + timedelta(hours=15),  # 11:00 AM EDT today
                end_time=today_start + timedelta(hours=16, minutes=30),
                chunk_index=1,
                total_chunks=2,
                is_completed=False,
            ),
            # Tomorrow's scheduled block
            ScheduleBlock(
                id=str(uuid.uuid4()),
                task_id=task_dict["Prepare Slide Deck for Hackathon Judges"].id,
                title="Prepare Slide Deck for Hackathon Judges",
                start_time=today_start + timedelta(days=1, hours=14, minutes=30),
                end_time=today_start + timedelta(days=1, hours=16),
                chunk_index=1,
                total_chunks=1,
                is_completed=False,
            ),
        ]
        db.add_all(blocks)

        # 6. Sample Plan Proposal (Agent proposed auto-rescheduling missed tasks)
        conv_id = str(uuid.uuid4())
        proposal = PlanProposal(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            status="draft_pending",
            summary="Auto-reschedule 2 overdue tasks into open afternoon focus slots",
            diff_payload={
                "added_blocks": [
                    {
                        "task_id": task_dict["Implement Staged Plan Diff Engine"].id,
                        "title": "Implement Staged Plan Diff Engine",
                        "start_time": (today_start + timedelta(hours=17)).isoformat() + "Z",
                        "end_time": (today_start + timedelta(hours=19)).isoformat() + "Z",
                        "chunk_index": 1,
                        "total_chunks": 1,
                    },
                    {
                        "task_id": task_dict["Synthesize Beta Feedback on Schedule Drift"].id,
                        "title": "Synthesize Beta Feedback on Schedule Drift",
                        "start_time": (today_start + timedelta(days=1, hours=16, minutes=30)).isoformat() + "Z",
                        "end_time": (today_start + timedelta(days=1, hours=17, minutes=30)).isoformat() + "Z",
                        "chunk_index": 1,
                        "total_chunks": 1,
                    },
                ],
                "shifted_blocks": [],
                "removed_blocks": [],
                "unscheduled_tasks": [],
            },
            snapshot_before={
                "scheduled_block_ids": [b.id for b in blocks],
                "missed_task_ids": [
                    task_dict["Implement Staged Plan Diff Engine"].id,
                    task_dict["Synthesize Beta Feedback on Schedule Drift"].id,
                ],
            },
        )
        db.add(proposal)
        db.flush()

        # Chat message for this proposal
        chat = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            sender="agent",
            content="I noticed you missed 2 tasks from yesterday: 'Implement Staged Plan Diff Engine' and 'Synthesize Beta Feedback'. I found open afternoon focus intervals today and tomorrow that fit within your 9am-5pm working hours. Review the proposed diff below.",
            proposal_id=proposal.id,
        )
        # 7. Historical Activity Logs for Insights & Trends
        activity_logs = [
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Design Deterministic Interval Scheduler"].id,
                action="completed",
                title="Design Deterministic Interval Scheduler",
                description="Completed deterministic interval scheduler ahead of deadline.",
                details={"planned_minutes": 90, "actual_minutes": 75, "category": "coding"},
                created_at=today_start - timedelta(days=2, hours=-15),
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Draft 1-Page Product Vision Memo"].id,
                action="completed",
                title="Draft 1-Page Product Vision Memo",
                description="Finished product vision draft memo.",
                details={"planned_minutes": 45, "actual_minutes": 50, "category": "writing"},
                created_at=today_start - timedelta(days=2, hours=-17),
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Setup Pytest Test Suite & Mocks"].id,
                action="completed",
                title="Setup Pytest Test Suite & Mocks",
                description="Setup full unit test suite with 100% coverage.",
                details={"planned_minutes": 45, "actual_minutes": 40, "category": "platform"},
                created_at=today_start - timedelta(days=1, hours=-11),
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Configure Timezone UTC Normalization"].id,
                action="completed",
                title="Configure Timezone UTC Normalization",
                description="Configured UTC timezone handler across FastAPI and SQLite.",
                details={"planned_minutes": 30, "actual_minutes": 35, "category": "platform"},
                created_at=today_start - timedelta(days=1, hours=-14),
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Implement Staged Plan Diff Engine"].id,
                action="missed",
                title="Implement Staged Plan Diff Engine",
                description="Ran out of time during late afternoon coding block.",
                details={"planned_minutes": 120, "actual_minutes": 150, "category": "coding"},
                created_at=today_start - timedelta(days=1, hours=-17),
            ),
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=task_dict["Synthesize Beta Feedback on Schedule Drift"].id,
                action="completed",
                title="Synthesize Beta Feedback on Schedule Drift",
                description="Compiled feedback notes from 5 beta testers.",
                details={"planned_minutes": 60, "actual_minutes": 65, "category": "study"},
                created_at=today_start - timedelta(days=3, hours=-14),
            ),
        ]
        db.add_all(activity_logs)

        db.commit()
        print(f"Successfully seeded demo workspace!")
        print(f"- 1 UserSettings (America/New_York, 9am-5pm)")
        print(f"- {len([goal_mvp, goal_pitch, goal_platform])} Goals")
        print(f"- {len(tasks)} Tasks ({len([t for t in tasks if t.status == 'completed'])} completed, {len([t for t in tasks if t.status == 'missed'])} missed/overdue)")
        print(f"- {len(fixed_events)} Fixed Events")
        print(f"- {len(blocks)} Schedule Blocks")
        print(f"- 1 Staged Plan Proposal with Agent Chat")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_database()
