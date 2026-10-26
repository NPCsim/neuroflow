from datetime import datetime, timezone, timedelta, time, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserSettings, Task, FixedEvent, ScheduleBlock, ActivityLog, Goal
from app.scheduler import (
    TaskInput,
    FixedEventInput,
    ScheduleSettingsInput,
    ScheduledBlock,
    build_schedule,
)
from app.feasibility import analyze_workload
from app.schemas.feasibility import (
    WorkloadAnalysisResponse,
    ScheduleRebuildRequest,
    ScheduleRebuildResponse,
    DayLoadResponse,
    WorkloadProblemResponse,
    RemedyOptionResponse,
    ScheduleBlockItemResponse,
    UnscheduledTaskItemResponse,
    StuckTaskResponse,
    RolloverTaskResponse,
    ActivityLogItemResponse,
    ScheduleRolloverRequest,
    ScheduleRolloverResponse,
    ScheduleOverviewResponse,
    FixedEventItemResponse,
    GoalSummaryResponse,
    ScheduleBlockStatusRequest,
    ScheduleRescheduleRequest,
    ApplyRemedyRequest,
)

router = APIRouter(tags=["Workload & Scheduling"])


def _get_or_create_settings(db: Session) -> UserSettings:
    settings = db.query(UserSettings).first()
    if not settings:
        settings = UserSettings(
            timezone="UTC",
            work_start_time="09:00",
            work_end_time="17:00",
            work_days=[0, 1, 2, 3, 4],
            buffer_minutes=10,
            min_chunk_minutes=30,
            max_chunk_minutes=120,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get(
    "/workload",
    response_model=WorkloadAnalysisResponse,
    summary="Analyze active workload feasibility",
    description="Calculates per-day load percentage, an overall realism score (0-100), and specific problems with machine-readable remedy options.",
)
def get_workload_analysis(
    horizon_days: int = 7,
    db: Session = Depends(get_db),
):
    try:
        user_settings = _get_or_create_settings(db)
        settings_input = ScheduleSettingsInput(
            timezone_str=user_settings.timezone,
            work_start_time=user_settings.work_start_time,
            work_end_time=user_settings.work_end_time,
            work_days=user_settings.work_days or [0, 1, 2, 3, 4],
            buffer_minutes=user_settings.buffer_minutes,
            min_chunk_minutes=user_settings.min_chunk_minutes,
            max_chunk_minutes=user_settings.max_chunk_minutes,
        )

        tasks = db.query(Task).filter(Task.status != "cancelled").all()
        blocks = db.query(ScheduleBlock).all()
        fixed_events = db.query(FixedEvent).all()

        task_inputs = [
            TaskInput(
                id=t.id,
                title=t.title,
                estimated_duration_minutes=t.estimated_duration_minutes,
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
                is_splittable=t.is_splittable,
                min_chunk_minutes=t.min_chunk_minutes,
                is_completed=(t.status == "completed"),
            )
            for t in tasks
        ]

        block_inputs = [
            ScheduledBlock(
                id=b.id,
                task_id=b.task_id or "",
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                chunk_index=b.chunk_index,
                total_chunks=b.total_chunks,
                is_completed=b.is_completed,
            )
            for b in blocks
        ]

        fixed_inputs = [
            FixedEventInput(
                id=fe.id,
                title=fe.title,
                start_time=fe.start_time,
                end_time=fe.end_time,
            )
            for fe in fixed_events
        ]

        result = analyze_workload(
            tasks=task_inputs,
            schedule=block_inputs,
            settings=settings_input,
            fixed_events=fixed_inputs,
            now=datetime.now(timezone.utc),
            horizon_days=horizon_days,
        )

        return WorkloadAnalysisResponse(
            realism_score=result.realism_score,
            status=result.status,
            daily_loads=[
                DayLoadResponse(
                    date=dl.date,
                    day_of_week=dl.day_of_week,
                    scheduled_minutes=dl.scheduled_minutes,
                    capacity_minutes=dl.capacity_minutes,
                    fixed_event_minutes=dl.fixed_event_minutes,
                    total_committed_minutes=dl.total_committed_minutes,
                    load_percentage=dl.load_percentage,
                    is_overloaded=dl.is_overloaded,
                )
                for dl in result.daily_loads
            ],
            problems=[
                WorkloadProblemResponse(
                    id=p.id,
                    task_id=p.task_id,
                    problem_type=p.problem_type,
                    description=p.description,
                    severity=p.severity,
                    hours_needed=p.hours_needed,
                    hours_available=p.hours_available,
                    remedies=[
                        RemedyOptionResponse(
                            action=r.action,
                            task_id=r.task_id,
                            title=r.title,
                            description=r.description,
                            parameters=r.parameters,
                            impact_hours=r.impact_hours,
                            impact_description=r.impact_description,
                        )
                        for r in p.remedies
                    ],
                )
                for p in result.problems
            ],
            total_scheduled_hours=result.total_scheduled_hours,
            total_capacity_hours=result.total_capacity_hours,
            total_fixed_event_hours=result.total_fixed_event_hours,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workload analysis failed: {str(e)}",
        )


@router.post(
    "/schedule/rebuild",
    response_model=ScheduleRebuildResponse,
    summary="Rebuild schedule from pending tasks and fixed events",
    description="Invokes the deterministic scheduler algorithm, replaces future schedule blocks in the database, and returns updated schedule and feasibility analysis.",
)
def rebuild_schedule(
    request: ScheduleRebuildRequest = ScheduleRebuildRequest(),
    db: Session = Depends(get_db),
):
    try:
        user_settings = _get_or_create_settings(db)
        settings_input = ScheduleSettingsInput(
            timezone_str=user_settings.timezone,
            work_start_time=user_settings.work_start_time,
            work_end_time=user_settings.work_end_time,
            work_days=user_settings.work_days or [0, 1, 2, 3, 4],
            buffer_minutes=user_settings.buffer_minutes,
            min_chunk_minutes=user_settings.min_chunk_minutes,
            max_chunk_minutes=user_settings.max_chunk_minutes,
        )

        now = request.start or datetime.now(timezone.utc)
        tasks = db.query(Task).filter(Task.status.in_(["pending", "scheduled", "missed"])).all()
        fixed_events = db.query(FixedEvent).all()

        task_inputs = [
            TaskInput(
                id=t.id,
                title=t.title,
                estimated_duration_minutes=t.estimated_duration_minutes,
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
                is_splittable=t.is_splittable,
                min_chunk_minutes=t.min_chunk_minutes,
                is_completed=(t.status == "completed"),
                is_carried_over=(t.status == "missed"),
            )
            for t in tasks
        ]

        fixed_inputs = [
            FixedEventInput(
                id=fe.id,
                title=fe.title,
                start_time=fe.start_time,
                end_time=fe.end_time,
            )
            for fe in fixed_events
        ]

        # 1. Run deterministic scheduler
        sched_res = build_schedule(
            tasks=task_inputs,
            fixed_events=fixed_inputs,
            settings=settings_input,
            start=now,
            horizon_days=request.horizon_days,
        )

        # 2. Database update: replace active uncompleted future blocks
        db.query(ScheduleBlock).filter(
            ScheduleBlock.is_completed == False,
            ScheduleBlock.start_time >= now,
        ).delete(synchronize_session=False)

        new_db_blocks = []
        for b in sched_res.blocks:
            new_db_blocks.append(
                ScheduleBlock(
                    id=b.id,
                    task_id=b.task_id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    chunk_index=b.chunk_index,
                    total_chunks=b.total_chunks,
                    is_completed=b.is_completed,
                )
            )

        db.add_all(new_db_blocks)

        # Update task status to 'scheduled' if placed
        scheduled_task_ids = {b.task_id for b in sched_res.blocks}
        for t in tasks:
            if t.id in scheduled_task_ids and t.status != "completed":
                t.status = "scheduled"

        db.commit()

        # 3. Analyze workload on newly rebuilt schedule
        analysis_res = analyze_workload(
            tasks=task_inputs,
            schedule=sched_res.blocks,
            settings=settings_input,
            fixed_events=fixed_inputs,
            now=now,
            horizon_days=request.horizon_days,
        )

        return ScheduleRebuildResponse(
            status="success",
            message=f"Rebuilt schedule: {len(sched_res.blocks)} blocks placed across {request.horizon_days} days.",
            scheduled_blocks_count=len(sched_res.blocks),
            unscheduled_tasks_count=len(sched_res.unscheduled_tasks),
            blocks=[
                ScheduleBlockItemResponse(
                    id=b.id,
                    task_id=b.task_id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    chunk_index=b.chunk_index,
                    total_chunks=b.total_chunks,
                    is_completed=b.is_completed,
                    is_at_risk=b.is_at_risk,
                )
                for b in sched_res.blocks
            ],
            unscheduled_tasks=[
                UnscheduledTaskItemResponse(
                    task_id=u.task_id,
                    title=u.title,
                    reason=u.reason,
                    at_risk=u.at_risk,
                    scheduled_minutes=u.scheduled_minutes,
                    remaining_minutes=u.remaining_minutes,
                    deadline=u.deadline,
                )
                for u in sched_res.unscheduled_tasks
            ],
            workload_analysis=WorkloadAnalysisResponse(
                realism_score=analysis_res.realism_score,
                status=analysis_res.status,
                daily_loads=[
                    DayLoadResponse(
                        date=dl.date,
                        day_of_week=dl.day_of_week,
                        scheduled_minutes=dl.scheduled_minutes,
                        capacity_minutes=dl.capacity_minutes,
                        fixed_event_minutes=dl.fixed_event_minutes,
                        total_committed_minutes=dl.total_committed_minutes,
                        load_percentage=dl.load_percentage,
                        is_overloaded=dl.is_overloaded,
                    )
                    for dl in analysis_res.daily_loads
                ],
                problems=[
                    WorkloadProblemResponse(
                        id=p.id,
                        task_id=p.task_id,
                        problem_type=p.problem_type,
                        description=p.description,
                        severity=p.severity,
                        hours_needed=p.hours_needed,
                        hours_available=p.hours_available,
                        remedies=[
                            RemedyOptionResponse(
                                action=r.action,
                                task_id=r.task_id,
                                title=r.title,
                                description=r.description,
                                parameters=r.parameters,
                                impact_hours=r.impact_hours,
                                impact_description=r.impact_description,
                            )
                            for r in p.remedies
                        ],
                    )
                    for p in analysis_res.problems
                ],
                total_scheduled_hours=analysis_res.total_scheduled_hours,
                total_capacity_hours=analysis_res.total_capacity_hours,
                total_fixed_event_hours=analysis_res.total_fixed_event_hours,
            ),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule rebuild failed: {str(e)}",
        )


@router.post(
    "/schedule/rollover",
    response_model=ScheduleRolloverResponse,
    summary="Roll over missed schedule blocks, update carry-over counts, and reschedule remaining work",
    description="Marks past uncompleted planned blocks as missed, logs them to activity_log, increments task carry-over counts, calls build_schedule to place remaining work, and flags tasks carried over 3+ times as stuck.",
)
def rollover_schedule(
    request: Optional[ScheduleRolloverRequest] = None,
    db: Session = Depends(get_db),
):
    req = request or ScheduleRolloverRequest()
    try:
        now = (
            req.now
            or req.start
            or req.current_time
            or datetime.now(timezone.utc)
        )
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Identify past planned blocks that weren't completed
        past_planned_blocks = (
            db.query(ScheduleBlock)
            .filter(
                ScheduleBlock.is_completed == False,
                ScheduleBlock.status != "missed",
                (ScheduleBlock.end_time <= now) | (ScheduleBlock.start_time < now),
            )
            .all()
        )

        # 2. Mark as missed, log to activity_log, and collect affected tasks
        new_activity_logs: list[ActivityLog] = []
        affected_tasks_dict: dict[str, Task] = {}

        for block in past_planned_blocks:
            block.status = "missed"
            block.is_completed = False
            block.updated_at = now

            log = ActivityLog(
                task_id=block.task_id,
                schedule_block_id=block.id,
                action="missed",
                entity_type="schedule_block",
                title=block.title,
                description=f"Schedule block '{block.title}' marked as missed during rollover",
                details={
                    "block_id": block.id,
                    "task_id": block.task_id,
                    "title": block.title,
                    "start_time": block.start_time.isoformat() if block.start_time else None,
                    "end_time": block.end_time.isoformat() if block.end_time else None,
                    "chunk_index": block.chunk_index,
                    "total_chunks": block.total_chunks,
                },
                created_at=now,
            )
            new_activity_logs.append(log)

            if block.task:
                affected_tasks_dict[block.task.id] = block.task
            elif block.task_id:
                t = db.query(Task).filter(Task.id == block.task_id).first()
                if t:
                    affected_tasks_dict[t.id] = t

        db.add_all(new_activity_logs)

        # 3. Increment carry-over counts on their tasks
        for task in affected_tasks_dict.values():
            task.carry_over_count = (task.carry_over_count or 0) + 1
            if task.status != "completed":
                task.status = "missed"
            task.updated_at = now

        # 4. Call build_schedule to place remaining work
        user_settings = _get_or_create_settings(db)
        settings_input = ScheduleSettingsInput(
            timezone_str=user_settings.timezone,
            work_start_time=user_settings.work_start_time,
            work_end_time=user_settings.work_end_time,
            work_days=user_settings.work_days or [0, 1, 2, 3, 4],
            buffer_minutes=user_settings.buffer_minutes,
            min_chunk_minutes=user_settings.min_chunk_minutes,
            max_chunk_minutes=user_settings.max_chunk_minutes,
        )

        active_tasks = (
            db.query(Task)
            .filter(
                Task.status.in_(["pending", "scheduled", "missed", "stuck"]),
                Task.status != "completed",
                Task.status != "cancelled",
            )
            .all()
        )
        fixed_events = db.query(FixedEvent).all()

        task_inputs = [
            TaskInput(
                id=t.id,
                title=t.title,
                estimated_duration_minutes=t.estimated_duration_minutes,
                remaining_duration_minutes=(
                    t.remaining_duration_minutes
                    if (t.remaining_duration_minutes is not None and t.remaining_duration_minutes > 0)
                    else t.estimated_duration_minutes
                ),
                priority=t.priority,
                deadline=t.deadline,
                is_splittable=t.is_splittable,
                min_chunk_minutes=t.min_chunk_minutes,
                is_completed=(t.status == "completed"),
                is_carried_over=((t.carry_over_count or 0) > 0 or t.status == "missed"),
            )
            for t in active_tasks
        ]

        fixed_inputs = [
            FixedEventInput(
                id=fe.id,
                title=fe.title,
                start_time=fe.start_time,
                end_time=fe.end_time,
            )
            for fe in fixed_events
        ]

        sched_res = build_schedule(
            tasks=task_inputs,
            fixed_events=fixed_inputs,
            settings=settings_input,
            start=now,
            horizon_days=req.horizon_days,
        )

        # 5. Database update: replace future uncompleted blocks from now onwards
        db.query(ScheduleBlock).filter(
            ScheduleBlock.is_completed == False,
            ScheduleBlock.status != "missed",
            ScheduleBlock.start_time >= now,
        ).delete(synchronize_session=False)

        new_db_blocks = []
        for b in sched_res.blocks:
            new_db_blocks.append(
                ScheduleBlock(
                    id=b.id,
                    task_id=b.task_id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    chunk_index=b.chunk_index,
                    total_chunks=b.total_chunks,
                    is_completed=b.is_completed,
                    status="planned",
                )
            )
        db.add_all(new_db_blocks)

        scheduled_task_ids = {b.task_id for b in sched_res.blocks}
        for t in active_tasks:
            if t.id in scheduled_task_ids and t.status != "completed":
                t.status = "scheduled"

        db.commit()

        # 6. Flag tasks carried over 3+ times as stuck in response
        all_tasks = db.query(Task).filter(Task.status != "cancelled").all()
        stuck_tasks_db = [
            t for t in all_tasks
            if (t.carry_over_count or 0) >= 3 and t.status != "completed"
        ]
        stuck_task_ids = [t.id for t in stuck_tasks_db]

        stuck_tasks_resp = [
            StuckTaskResponse(
                id=t.id,
                title=t.title,
                carry_over_count=t.carry_over_count or 0,
                status="stuck" if t.status != "completed" else t.status,
                is_stuck=True,
                flag="stuck",
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
            )
            for t in stuck_tasks_db
        ]

        carried_tasks_resp = [
            RolloverTaskResponse(
                id=t.id,
                title=t.title,
                carry_over_count=t.carry_over_count or 0,
                status=t.status,
                is_stuck=((t.carry_over_count or 0) >= 3),
                flag="stuck" if ((t.carry_over_count or 0) >= 3) else None,
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
            )
            for t in affected_tasks_dict.values()
        ]

        tasks_resp = [
            RolloverTaskResponse(
                id=t.id,
                title=t.title,
                carry_over_count=t.carry_over_count or 0,
                status=t.status,
                is_stuck=((t.carry_over_count or 0) >= 3),
                flag="stuck" if ((t.carry_over_count or 0) >= 3) else None,
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
            )
            for t in all_tasks
            if t.status != "completed"
        ]

        missed_blocks_resp = [
            ScheduleBlockItemResponse(
                id=b.id,
                task_id=b.task_id,
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                chunk_index=b.chunk_index,
                total_chunks=b.total_chunks,
                is_completed=b.is_completed,
                is_at_risk=False,
                status="missed",
                is_stuck=(b.task_id in stuck_task_ids),
            )
            for b in past_planned_blocks
        ]

        blocks_resp = [
            ScheduleBlockItemResponse(
                id=b.id,
                task_id=b.task_id,
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                chunk_index=b.chunk_index,
                total_chunks=b.total_chunks,
                is_completed=b.is_completed,
                is_at_risk=b.is_at_risk,
                status="planned",
                is_stuck=(b.task_id in stuck_task_ids),
            )
            for b in sched_res.blocks
        ]

        task_map = {t.id: t for t in all_tasks}
        unscheduled_resp = [
            UnscheduledTaskItemResponse(
                task_id=u.task_id,
                title=u.title,
                reason=u.reason,
                at_risk=u.at_risk,
                scheduled_minutes=u.scheduled_minutes,
                remaining_minutes=u.remaining_minutes,
                deadline=u.deadline,
                is_stuck=(u.task_id in stuck_task_ids),
                flag="stuck" if (u.task_id in stuck_task_ids) else None,
                carry_over_count=task_map[u.task_id].carry_over_count if u.task_id in task_map else 0,
            )
            for u in sched_res.unscheduled_tasks
        ]

        activity_logs_resp = [
            ActivityLogItemResponse(
                id=l.id,
                task_id=l.task_id,
                schedule_block_id=l.schedule_block_id,
                action=l.action,
                title=l.title,
                description=l.description,
                details=l.details,
                created_at=l.created_at,
            )
            for l in new_activity_logs
        ]

        analysis_res = analyze_workload(
            tasks=task_inputs,
            schedule=sched_res.blocks,
            settings=settings_input,
            fixed_events=fixed_inputs,
            now=now,
            horizon_days=req.horizon_days,
        )

        return ScheduleRolloverResponse(
            status="success",
            message=f"Rollover complete: marked {len(past_planned_blocks)} block(s) missed, carried over {len(affected_tasks_dict)} task(s), {len(stuck_tasks_resp)} stuck task(s) flagged.",
            rollover_time=now,
            missed_blocks_count=len(past_planned_blocks),
            carried_over_tasks_count=len(affected_tasks_dict),
            stuck_tasks_count=len(stuck_tasks_resp),
            stuck_tasks=stuck_tasks_resp,
            stuck_task_ids=stuck_task_ids,
            carried_over_tasks=carried_tasks_resp,
            tasks=tasks_resp,
            missed_blocks=missed_blocks_resp,
            blocks=blocks_resp,
            scheduled_blocks=blocks_resp,
            scheduled_blocks_count=len(blocks_resp),
            unscheduled_tasks=unscheduled_resp,
            unscheduled_tasks_count=len(unscheduled_resp),
            activity_logs=activity_logs_resp,
            workload_analysis=WorkloadAnalysisResponse(
                realism_score=analysis_res.realism_score,
                status=analysis_res.status,
                daily_loads=[
                    DayLoadResponse(
                        date=dl.date,
                        day_of_week=dl.day_of_week,
                        scheduled_minutes=dl.scheduled_minutes,
                        capacity_minutes=dl.capacity_minutes,
                        fixed_event_minutes=dl.fixed_event_minutes,
                        total_committed_minutes=dl.total_committed_minutes,
                        load_percentage=dl.load_percentage,
                        is_overloaded=dl.is_overloaded,
                    )
                    for dl in analysis_res.daily_loads
                ],
                problems=[
                    WorkloadProblemResponse(
                        id=p.id,
                        task_id=p.task_id,
                        problem_type=p.problem_type,
                        description=p.description,
                        severity=p.severity,
                        hours_needed=p.hours_needed,
                        hours_available=p.hours_available,
                        remedies=[
                            RemedyOptionResponse(
                                action=r.action,
                                task_id=r.task_id,
                                title=r.title,
                                description=r.description,
                                parameters=r.parameters,
                                impact_hours=r.impact_hours,
                                impact_description=r.impact_description,
                            )
                            for r in p.remedies
                        ],
                    )
                    for p in analysis_res.problems
                ],
                total_scheduled_hours=analysis_res.total_scheduled_hours,
                total_capacity_hours=analysis_res.total_capacity_hours,
                total_fixed_event_hours=analysis_res.total_fixed_event_hours,
            ),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule rollover failed: {str(e)}",
        )


GOAL_PALETTE = ["indigo", "emerald", "cyan", "amber", "purple", "pink"]


def _get_goal_color(goal_id: Optional[str], goals_list: list) -> str:
    if not goal_id:
        return "indigo"
    for idx, g in enumerate(goals_list):
        if g.id == goal_id:
            return GOAL_PALETTE[idx % len(GOAL_PALETTE)]
    return "indigo"


@router.get(
    "/schedule",
    response_model=ScheduleOverviewResponse,
    summary="Get full schedule overview including blocks, fixed events, goals, and workload",
)
def get_schedule(
    horizon_days: int = 7,
    start: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    try:
        user_settings = _get_or_create_settings(db)
        settings_input = ScheduleSettingsInput(
            timezone_str=user_settings.timezone,
            work_start_time=user_settings.work_start_time,
            work_end_time=user_settings.work_end_time,
            work_days=user_settings.work_days or [0, 1, 2, 3, 4],
            buffer_minutes=user_settings.buffer_minutes,
            min_chunk_minutes=user_settings.min_chunk_minutes,
            max_chunk_minutes=user_settings.max_chunk_minutes,
        )

        now = start or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        goals = db.query(Goal).all()
        goal_responses = [
            GoalSummaryResponse(
                id=g.id,
                title=g.title,
                description=g.description,
                color=_get_goal_color(g.id, goals),
            )
            for g in goals
        ]

        fixed_events = db.query(FixedEvent).all()
        fixed_responses = [
            FixedEventItemResponse(
                id=fe.id,
                title=fe.title,
                start_time=fe.start_time,
                end_time=fe.end_time,
                source=fe.source,
            )
            for fe in fixed_events
        ]

        tasks = db.query(Task).filter(Task.status != "cancelled").all()
        blocks = db.query(ScheduleBlock).all()

        task_inputs = [
            TaskInput(
                id=t.id,
                title=t.title,
                estimated_duration_minutes=t.estimated_duration_minutes,
                remaining_duration_minutes=t.remaining_duration_minutes,
                priority=t.priority,
                deadline=t.deadline,
                is_splittable=t.is_splittable,
                min_chunk_minutes=t.min_chunk_minutes,
                is_completed=(t.status == "completed"),
                is_carried_over=((t.carry_over_count or 0) > 0 or t.status == "missed"),
            )
            for t in tasks
        ]

        block_inputs = [
            ScheduledBlock(
                id=b.id,
                task_id=b.task_id or "",
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                chunk_index=b.chunk_index,
                total_chunks=b.total_chunks,
                is_completed=b.is_completed,
            )
            for b in blocks
        ]

        fixed_inputs = [
            FixedEventInput(
                id=fe.id,
                title=fe.title,
                start_time=fe.start_time,
                end_time=fe.end_time,
            )
            for fe in fixed_events
        ]

        analysis_res = analyze_workload(
            tasks=task_inputs,
            schedule=block_inputs,
            settings=settings_input,
            fixed_events=fixed_inputs,
            now=now,
            horizon_days=horizon_days,
        )

        at_risk_task_ids = set()
        for p in analysis_res.problems:
            if p.task_id:
                at_risk_task_ids.add(p.task_id)

        stuck_task_ids = {t.id for t in tasks if (t.carry_over_count or 0) >= 3}

        block_responses: list[ScheduleBlockItemResponse] = []
        for b in blocks:
            task = b.task
            goal_id = task.goal_id if (task and task.goal_id) else None
            goal_title = task.goal.title if (task and task.goal) else None
            goal_color = _get_goal_color(goal_id, goals)

            is_risk = False
            if b.task_id and b.task_id in at_risk_task_ids:
                is_risk = True
            if task and task.deadline:
                dl = task.deadline if task.deadline.tzinfo else task.deadline.replace(tzinfo=timezone.utc)
                b_end = b.end_time if b.end_time.tzinfo else b.end_time.replace(tzinfo=timezone.utc)
                if b_end > dl:
                    is_risk = True

            block_responses.append(
                ScheduleBlockItemResponse(
                    id=b.id,
                    task_id=b.task_id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    chunk_index=b.chunk_index,
                    total_chunks=b.total_chunks,
                    is_completed=b.is_completed,
                    is_at_risk=is_risk,
                    status=b.status or ("completed" if b.is_completed else "planned"),
                    is_stuck=(b.task_id in stuck_task_ids if b.task_id else False),
                    goal_id=goal_id,
                    goal_title=goal_title,
                    goal_color=goal_color,
                    priority=task.priority if task else "normal",
                    deadline=task.deadline if task else None,
                )
            )

        today_str = now.strftime("%Y-%m-%d")
        today_load = None
        for dl in analysis_res.daily_loads:
            if dl.date == today_str:
                today_load = DayLoadResponse(
                    date=dl.date,
                    day_of_week=dl.day_of_week,
                    scheduled_minutes=dl.scheduled_minutes,
                    capacity_minutes=dl.capacity_minutes,
                    fixed_event_minutes=dl.fixed_event_minutes,
                    total_committed_minutes=dl.total_committed_minutes,
                    load_percentage=dl.load_percentage,
                    is_overloaded=dl.is_overloaded,
                )
                break
        if not today_load and analysis_res.daily_loads:
            today_load = DayLoadResponse(
                date=analysis_res.daily_loads[0].date,
                day_of_week=analysis_res.daily_loads[0].day_of_week,
                scheduled_minutes=analysis_res.daily_loads[0].scheduled_minutes,
                capacity_minutes=analysis_res.daily_loads[0].capacity_minutes,
                fixed_event_minutes=analysis_res.daily_loads[0].fixed_event_minutes,
                total_committed_minutes=analysis_res.daily_loads[0].total_committed_minutes,
                load_percentage=analysis_res.daily_loads[0].load_percentage,
                is_overloaded=analysis_res.daily_loads[0].is_overloaded,
            )

        workload_resp = WorkloadAnalysisResponse(
            realism_score=analysis_res.realism_score,
            status=analysis_res.status,
            daily_loads=[
                DayLoadResponse(
                    date=dl.date,
                    day_of_week=dl.day_of_week,
                    scheduled_minutes=dl.scheduled_minutes,
                    capacity_minutes=dl.capacity_minutes,
                    fixed_event_minutes=dl.fixed_event_minutes,
                    total_committed_minutes=dl.total_committed_minutes,
                    load_percentage=dl.load_percentage,
                    is_overloaded=dl.is_overloaded,
                )
                for dl in analysis_res.daily_loads
            ],
            problems=[
                WorkloadProblemResponse(
                    id=p.id,
                    task_id=p.task_id,
                    problem_type=p.problem_type,
                    description=p.description,
                    severity=p.severity,
                    hours_needed=p.hours_needed,
                    hours_available=p.hours_available,
                    remedies=[
                        RemedyOptionResponse(
                            action=r.action,
                            task_id=r.task_id,
                            title=r.title,
                            description=r.description,
                            parameters=r.parameters,
                            impact_hours=r.impact_hours,
                            impact_description=r.impact_description,
                        )
                        for r in p.remedies
                    ],
                )
                for p in analysis_res.problems
            ],
            total_scheduled_hours=analysis_res.total_scheduled_hours,
            total_capacity_hours=analysis_res.total_capacity_hours,
            total_fixed_event_hours=analysis_res.total_fixed_event_hours,
        )

        return ScheduleOverviewResponse(
            status="success",
            current_time=now,
            blocks=block_responses,
            fixed_events=fixed_responses,
            goals=goal_responses,
            workload=workload_resp,
            today=today_load,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schedule overview: {str(e)}",
        )


@router.post(
    "/schedule/blocks/{block_id}/status",
    summary="Update block completion / missed status (plural alias)",
)
@router.post(
    "/schedule/block/{block_id}/status",
    summary="Update block completion / missed status",
)
def update_block_status(
    block_id: str,
    request: ScheduleBlockStatusRequest,
    db: Session = Depends(get_db),
):
    block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule block not found.")

    now = datetime.now(timezone.utc)
    target_status = request.status.lower()
    if target_status not in ["completed", "missed", "planned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'completed', 'missed', or 'planned'.",
        )

    block.status = target_status
    block.is_completed = (target_status == "completed")
    block.updated_at = now

    task = block.task
    if task:
        if target_status == "completed":
            dur = int((block.end_time - block.start_time).total_seconds() / 60) if (block.end_time and block.start_time) else 60
            task.remaining_duration_minutes = max(0, (task.remaining_duration_minutes or task.estimated_duration_minutes) - dur)
            remaining_uncompleted = db.query(ScheduleBlock).filter(
                ScheduleBlock.task_id == task.id,
                ScheduleBlock.id != block.id,
                ScheduleBlock.is_completed == False,
            ).count()
            if remaining_uncompleted == 0 or task.remaining_duration_minutes == 0:
                task.status = "completed"
        elif target_status == "missed":
            task.carry_over_count = (task.carry_over_count or 0) + 1
            if task.status != "completed":
                task.status = "missed"
        elif target_status == "planned":
            if task.status == "completed":
                task.status = "scheduled"
        task.updated_at = now

    log = ActivityLog(
        task_id=block.task_id,
        schedule_block_id=block.id,
        action=f"block_{target_status}",
        title=block.title,
        description=f"Block '{block.title}' marked as {target_status}",
        details={"block_id": block.id, "status": target_status},
        created_at=now,
    )
    db.add(log)
    db.commit()

    return {
        "status": "success",
        "message": f"Block marked as {target_status}.",
        "block_id": block.id,
        "block_status": target_status,
        "is_completed": block.is_completed,
    }


@router.post(
    "/schedule/reschedule",
    summary="Reschedule a block with backend conflict re-validation",
)
def reschedule_block(
    request: ScheduleRescheduleRequest,
    db: Session = Depends(get_db),
):
    block = db.query(ScheduleBlock).filter(ScheduleBlock.id == request.block_id).first()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule block not found.")

    new_start = request.new_start
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    orig_dur = int((block.end_time - block.start_time).total_seconds() / 60) if (block.end_time and block.start_time) else 60
    if request.new_end:
        new_end = request.new_end
        if new_end.tzinfo is None:
            new_end = new_end.replace(tzinfo=timezone.utc)
    else:
        new_end = new_start + timedelta(minutes=orig_dur)

    if new_end <= new_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New end time must be after new start time.")

    # 1. Conflict Re-validation with Fixed Events
    fixed_events = db.query(FixedEvent).all()
    for fe in fixed_events:
        fe_start = fe.start_time if fe.start_time.tzinfo else fe.start_time.replace(tzinfo=timezone.utc)
        fe_end = fe.end_time if fe.end_time.tzinfo else fe.end_time.replace(tzinfo=timezone.utc)
        if max(new_start, fe_start) < min(new_end, fe_end):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Re-validation failed: Overlaps with fixed event '{fe.title}' ({fe_start.strftime('%H:%M')} - {fe_end.strftime('%H:%M')}).",
            )

    # 2. Conflict Re-validation with other active scheduled blocks
    other_blocks = db.query(ScheduleBlock).filter(
        ScheduleBlock.id != block.id,
        ScheduleBlock.is_completed == False,
        ScheduleBlock.status != "missed",
    ).all()
    for ob in other_blocks:
        ob_start = ob.start_time if ob.start_time.tzinfo else ob.start_time.replace(tzinfo=timezone.utc)
        ob_end = ob.end_time if ob.end_time.tzinfo else ob.end_time.replace(tzinfo=timezone.utc)
        if max(new_start, ob_start) < min(new_end, ob_end):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Re-validation failed: Overlaps with scheduled block '{ob.title}' ({ob_start.strftime('%H:%M')} - {ob_end.strftime('%H:%M')}).",
            )

    # 3. Check Working Hours and Work Days constraints from UserSettings
    user_settings = _get_or_create_settings(db)
    work_start_h, work_start_m = [int(p) for p in (user_settings.work_start_time or "09:00").split(":")]
    work_end_h, work_end_m = [int(p) for p in (user_settings.work_end_time or "17:00").split(":")]

    try:
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo(user_settings.timezone) if user_settings.timezone else timezone.utc
    except Exception:
        user_tz = timezone.utc

    local_start = new_start.astimezone(user_tz)
    local_end = new_end.astimezone(user_tz)

    work_days = user_settings.work_days if user_settings.work_days is not None else [0, 1, 2, 3, 4]
    if local_start.weekday() not in work_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Re-validation failed: Selected date is not a configured work day.",
        )

    day_start = datetime.combine(local_start.date(), time(work_start_h, work_start_m, 0), tzinfo=user_tz)
    day_end = datetime.combine(local_start.date(), time(work_end_h, work_end_m, 0), tzinfo=user_tz)

    if local_start < day_start or local_end > day_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Re-validation failed: Slot ({local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}) is outside working hours ({user_settings.work_start_time} - {user_settings.work_end_time}).",
        )

    # Update block
    old_start = block.start_time
    block.start_time = new_start
    block.end_time = new_end
    block.updated_at = datetime.now(timezone.utc)

    # Deadline risk check
    is_at_risk = False
    warning_msg = None
    task = block.task
    if task and task.deadline:
        dl = task.deadline if task.deadline.tzinfo else task.deadline.replace(tzinfo=timezone.utc)
        if new_end > dl:
            is_at_risk = True
            warning_msg = f"Task deadline is {dl.strftime('%Y-%m-%d %H:%M')}; block finishes after deadline."

    log = ActivityLog(
        task_id=block.task_id,
        schedule_block_id=block.id,
        action="rescheduled",
        title=block.title,
        description=f"Block '{block.title}' rescheduled to {new_start.strftime('%Y-%m-%d %H:%M')}",
        details={
            "block_id": block.id,
            "old_start": old_start.isoformat() if old_start else None,
            "new_start": new_start.isoformat(),
            "new_end": new_end.isoformat(),
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(block)

    return {
        "status": "success",
        "message": f"Block '{block.title}' rescheduled successfully.",
        "warning": warning_msg,
        "is_at_risk": is_at_risk,
        "block": {
            "id": block.id,
            "title": block.title,
            "start_time": block.start_time.isoformat(),
            "end_time": block.end_time.isoformat(),
            "is_at_risk": is_at_risk,
        },
    }


@router.post(
    "/workload/remedy",
    summary="Apply machine-readable workload remedy (alias)",
)
@router.post(
    "/workload/remedy/apply",
    summary="Apply machine-readable workload remedy and rebuild schedule",
)
def apply_workload_remedy(
    request: ApplyRemedyRequest,
    db: Session = Depends(get_db),
):
    action = request.action.lower()
    task = None
    if request.task_id:
        task = db.query(Task).filter(Task.id == request.task_id).first()

    now = datetime.now(timezone.utc)
    applied_desc = ""

    if action in ["extend_deadline", "defer_task"]:
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found for deadline extension.")
        days_to_add = request.parameters.get("days", 3)
        curr_dl = task.deadline or (now + timedelta(days=2))
        task.deadline = curr_dl + timedelta(days=days_to_add)
        task.updated_at = now
        applied_desc = f"Extended deadline for '{task.title}' by {days_to_add} days."

    elif action in ["reduce_scope", "shorten_task"]:
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found for scope reduction.")
        pct = request.parameters.get("reduction_percentage", 30)
        reduction = int(task.estimated_duration_minutes * (pct / 100))
        new_dur = max(15, task.estimated_duration_minutes - reduction)
        task.estimated_duration_minutes = new_dur
        task.remaining_duration_minutes = new_dur
        task.updated_at = now
        applied_desc = f"Reduced scope for '{task.title}' to {new_dur} mins ({pct}% reduction)."

    elif action in ["split_task", "enable_splitting"]:
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found for splitting.")
        task.is_splittable = True
        task.min_chunk_minutes = request.parameters.get("min_chunk_minutes", 30)
        task.updated_at = now
        applied_desc = f"Enabled splittable chunks for '{task.title}'."

    elif action in ["drop_task", "cancel_task"]:
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found to drop.")
        task.status = "cancelled"
        task.updated_at = now
        db.query(ScheduleBlock).filter(ScheduleBlock.task_id == task.id).delete()
        applied_desc = f"Dropped task '{task.title}'."

    elif action in ["add_capacity", "extend_hours"]:
        settings = _get_or_create_settings(db)
        settings.work_end_time = "19:00"
        applied_desc = "Extended working hours to 19:00 to increase daily capacity."

    else:
        applied_desc = f"Applied remedy '{action}'."

    db.commit()

    # Rebuild schedule automatically
    user_settings = _get_or_create_settings(db)
    settings_input = ScheduleSettingsInput(
        timezone_str=user_settings.timezone,
        work_start_time=user_settings.work_start_time,
        work_end_time=user_settings.work_end_time,
        work_days=user_settings.work_days or [0, 1, 2, 3, 4],
        buffer_minutes=user_settings.buffer_minutes,
        min_chunk_minutes=user_settings.min_chunk_minutes,
        max_chunk_minutes=user_settings.max_chunk_minutes,
    )

    tasks = db.query(Task).filter(Task.status.in_(["pending", "scheduled", "missed"])).all()
    fixed_events = db.query(FixedEvent).all()

    task_inputs = [
        TaskInput(
            id=t.id,
            title=t.title,
            estimated_duration_minutes=t.estimated_duration_minutes,
            remaining_duration_minutes=t.remaining_duration_minutes,
            priority=t.priority,
            deadline=t.deadline,
            is_splittable=t.is_splittable,
            min_chunk_minutes=t.min_chunk_minutes,
            is_completed=(t.status == "completed"),
        )
        for t in tasks
    ]
    fixed_inputs = [
        FixedEventInput(
            id=fe.id,
            title=fe.title,
            start_time=fe.start_time,
            end_time=fe.end_time,
        )
        for fe in fixed_events
    ]

    sched_res = build_schedule(
        tasks=task_inputs,
        fixed_events=fixed_inputs,
        settings=settings_input,
        start=now,
        horizon_days=7,
    )

    db.query(ScheduleBlock).filter(
        ScheduleBlock.is_completed == False,
        ScheduleBlock.start_time >= now,
    ).delete(synchronize_session=False)

    new_blocks = [
        ScheduleBlock(
            id=b.id,
            task_id=b.task_id,
            title=b.title,
            start_time=b.start_time,
            end_time=b.end_time,
            chunk_index=b.chunk_index,
            total_chunks=b.total_chunks,
            is_completed=b.is_completed,
            status="planned",
        )
        for b in sched_res.blocks
    ]
    db.add_all(new_blocks)
    db.commit()

    analysis_res = analyze_workload(
        tasks=task_inputs,
        schedule=sched_res.blocks,
        settings=settings_input,
        fixed_events=fixed_inputs,
        now=now,
        horizon_days=7,
    )

    return {
        "status": "success",
        "message": applied_desc,
        "action": action,
        "realism_score": analysis_res.realism_score,
        "problems_remaining": len(analysis_res.problems),
    }
