from __future__ import annotations

import uuid
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from google.genai import types

from app.models import UserSettings, Task, FixedEvent, ScheduleBlock, ActivityLog
from app.scheduler import (
    TaskInput,
    FixedEventInput,
    ScheduleSettingsInput,
    ScheduledBlock,
    build_schedule,
)


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
        db.flush()
    return settings


def _find_task(db: Session, task_id: str) -> Optional[Task]:
    """Finds a task by ID first; falls back to case-insensitive title matching."""
    if not task_id:
        return None
    task = db.query(Task).filter(Task.id == str(task_id)).first()
    if not task:
        # Fallback by title or partial title
        task = db.query(Task).filter(Task.title.ilike(f"%{task_id}%")).first()
    return task


def _parse_target_datetime(val: Any, reference_time: Optional[datetime] = None) -> datetime:
    """Parses various date/time expressions into a timezone-aware UTC datetime."""
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)

    if isinstance(val, date):
        return datetime.combine(val, time(17, 0, 0, tzinfo=timezone.utc))

    if not isinstance(val, str):
        return now + timedelta(days=1)

    s = val.strip().lower()
    if s == "today":
        return datetime.combine(now.date(), time(17, 0, 0, tzinfo=timezone.utc))
    elif s == "tomorrow":
        return datetime.combine(now.date() + timedelta(days=1), time(17, 0, 0, tzinfo=timezone.utc))

    weekdays = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }
    for day_name, day_idx in weekdays.items():
        if day_name in s:
            days_ahead = (day_idx - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target_date = now.date() + timedelta(days=days_ahead)
            return datetime.combine(target_date, time(17, 0, 0, tzinfo=timezone.utc))

    # Try ISO formats
    clean_val = val.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Try YYYY-MM-DD
    try:
        d = date.fromisoformat(val.strip())
        return datetime.combine(d, time(17, 0, 0, tzinfo=timezone.utc))
    except Exception:
        pass

    return now + timedelta(days=1)


def _map_importance(importance: Any) -> str:
    """Maps 1-5 or strings to priority column values."""
    if isinstance(importance, int):
        if importance >= 5:
            return "urgent_important"
        elif importance == 4:
            return "important"
        elif importance == 3:
            return "normal"
        else:
            return "low"

    s = str(importance).strip().lower()
    if s in ["5", "urgent", "urgent_important", "top", "highest"]:
        return "urgent_important"
    elif s in ["4", "important", "high"]:
        return "important"
    elif s in ["3", "normal", "medium"]:
        return "normal"
    elif s in ["1", "2", "low"]:
        return "low"
    return "normal"


# ---------------------------------------------------------------------------
# Service Functions for Tools
# ---------------------------------------------------------------------------

def service_get_plan(
    db: Session,
    range_val: str = "today",
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Retrieves current scheduled blocks and active tasks within range."""
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Determine window
    s = str(range_val).strip().lower()
    if s in ["today", "1_day"]:
        start_dt = datetime.combine(now.date(), time(0, 0, 0, tzinfo=timezone.utc))
        end_dt = datetime.combine(now.date(), time(23, 59, 59, tzinfo=timezone.utc))
    elif s in ["tomorrow"]:
        start_dt = datetime.combine(now.date() + timedelta(days=1), time(0, 0, 0, tzinfo=timezone.utc))
        end_dt = datetime.combine(now.date() + timedelta(days=1), time(23, 59, 59, tzinfo=timezone.utc))
    elif s in ["this_week", "7_days", "week"]:
        start_dt = datetime.combine(now.date(), time(0, 0, 0, tzinfo=timezone.utc))
        end_dt = start_dt + timedelta(days=7)
    else:
        start_dt = datetime.combine(now.date(), time(0, 0, 0, tzinfo=timezone.utc))
        end_dt = start_dt + timedelta(days=7)

    blocks = (
        db.query(ScheduleBlock)
        .filter(
            ScheduleBlock.end_time >= start_dt,
            ScheduleBlock.start_time <= end_dt,
        )
        .order_by(ScheduleBlock.start_time.asc())
        .all()
    )

    tasks = (
        db.query(Task)
        .filter(Task.status.in_(["pending", "scheduled", "missed", "stuck"]))
        .all()
    )

    return {
        "range": range_val,
        "window_start": start_dt.isoformat(),
        "window_end": end_dt.isoformat(),
        "scheduled_blocks_count": len(blocks),
        "scheduled_blocks": [
            {
                "id": b.id,
                "task_id": b.task_id,
                "title": b.title,
                "start_time": b.start_time.isoformat() if b.start_time else None,
                "end_time": b.end_time.isoformat() if b.end_time else None,
                "chunk_index": b.chunk_index,
                "total_chunks": b.total_chunks,
                "is_completed": b.is_completed,
                "status": b.status,
            }
            for b in blocks
        ],
        "active_tasks_count": len(tasks),
        "active_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "estimated_duration_minutes": t.estimated_duration_minutes,
                "remaining_duration_minutes": t.remaining_duration_minutes,
                "status": t.status,
                "is_splittable": t.is_splittable,
            }
            for t in tasks
        ],
    }


def service_move_task(
    db: Session,
    task_id: str,
    new_start: str,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Moves a task's schedule block to start at new_start."""
    task = _find_task(db, task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    start_dt = _parse_target_datetime(new_start, reference_time)
    duration_minutes = task.remaining_duration_minutes or task.estimated_duration_minutes or 60
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    # Look for existing blocks
    blocks = db.query(ScheduleBlock).filter(ScheduleBlock.task_id == task.id).all()
    if blocks:
        for b in blocks:
            b_dur = int((b.end_time - b.start_time).total_seconds() / 60) if (b.start_time and b.end_time) else duration_minutes
            b.start_time = start_dt
            b.end_time = start_dt + timedelta(minutes=b_dur)
            b.updated_at = reference_time or datetime.now(timezone.utc)
    else:
        new_block = ScheduleBlock(
            id=str(uuid.uuid4()),
            task_id=task.id,
            title=task.title,
            start_time=start_dt,
            end_time=end_dt,
            chunk_index=1,
            total_chunks=1,
            status="planned",
        )
        db.add(new_block)

    task.status = "scheduled"
    task.updated_at = reference_time or datetime.now(timezone.utc)
    db.flush()

    return {
        "status": "success",
        "task_id": task.id,
        "title": task.title,
        "new_start": start_dt.isoformat(),
        "new_end": end_dt.isoformat(),
    }


def service_split_task(
    db: Session,
    task_id: str,
    parts: int = 2,
) -> Dict[str, Any]:
    """Enables splitting for a task and computes chunk minimums."""
    task = _find_task(db, task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    num_parts = max(2, int(parts or 2))
    task.is_splittable = True
    total_mins = task.remaining_duration_minutes or task.estimated_duration_minutes or 60
    chunk_size = max(15, total_mins // num_parts)
    task.min_chunk_minutes = chunk_size
    task.updated_at = datetime.now(timezone.utc)
    db.flush()

    return {
        "status": "success",
        "task_id": task.id,
        "title": task.title,
        "is_splittable": True,
        "parts": num_parts,
        "min_chunk_minutes": chunk_size,
    }


def service_defer_task(
    db: Session,
    task_id: str,
    new_deadline: str,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Defers a task by extending its deadline."""
    task = _find_task(db, task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    old_deadline = task.deadline
    new_deadline_dt = _parse_target_datetime(new_deadline, reference_time)

    task.deadline = new_deadline_dt
    task.updated_at = reference_time or datetime.now(timezone.utc)
    db.flush()

    return {
        "status": "success",
        "task_id": task.id,
        "title": task.title,
        "old_deadline": old_deadline.isoformat() if old_deadline else None,
        "new_deadline": new_deadline_dt.isoformat(),
    }


def service_set_priority(
    db: Session,
    task_id: str,
    importance: Any,
) -> Dict[str, Any]:
    """Adjusts priority / importance for a task."""
    task = _find_task(db, task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    new_prio = _map_importance(importance)
    task.priority = new_prio
    task.updated_at = datetime.now(timezone.utc)
    db.flush()

    return {
        "status": "success",
        "task_id": task.id,
        "title": task.title,
        "priority": task.priority,
    }


def service_add_task(
    db: Session,
    title: str,
    est_minutes: int,
    importance: Any = 3,
    deadline: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Adds a new task to be scheduled."""
    if not title:
        return {"error": "Task title is required"}

    deadline_dt = _parse_target_datetime(deadline, reference_time) if deadline else None
    prio = _map_importance(importance)
    duration = max(10, int(est_minutes or 60))

    new_task = Task(
        id=str(uuid.uuid4()),
        title=title.strip(),
        description=description,
        estimated_duration_minutes=duration,
        remaining_duration_minutes=duration,
        priority=prio,
        deadline=deadline_dt,
        is_splittable=True,
        min_chunk_minutes=30,
        status="pending",
        carry_over_count=0,
    )
    db.add(new_task)
    db.flush()

    return {
        "status": "success",
        "task_id": new_task.id,
        "title": new_task.title,
        "estimated_duration_minutes": new_task.estimated_duration_minutes,
        "priority": new_task.priority,
        "deadline": deadline_dt.isoformat() if deadline_dt else None,
    }


def service_mark_done(
    db: Session,
    task_id: str,
) -> Dict[str, Any]:
    """Marks a task as completed."""
    task = _find_task(db, task_id)
    if not task:
        return {"error": f"Task not found: {task_id}"}

    task.status = "completed"
    task.remaining_duration_minutes = 0
    task.updated_at = datetime.now(timezone.utc)

    # Complete associated blocks
    blocks = db.query(ScheduleBlock).filter(ScheduleBlock.task_id == task.id).all()
    for b in blocks:
        b.is_completed = True
        b.status = "completed"
        b.updated_at = datetime.now(timezone.utc)

    db.flush()
    return {
        "status": "success",
        "task_id": task.id,
        "title": task.title,
        "task_status": "completed",
    }


def service_reduce_available_time(
    db: Session,
    date_val: str = "today",
    minutes_lost: int = 180,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Reduces available work capacity on date_val by inserting a fixed constraint event."""
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    target_dt = _parse_target_datetime(date_val, now)
    target_date = target_dt.date()

    user_settings = _get_or_create_settings(db)
    work_end_str = user_settings.work_end_time or "17:00"
    end_h, end_m = [int(p) for p in work_end_str.split(":")]
    day_work_end = datetime.combine(target_date, time(end_h, end_m, 0, tzinfo=timezone.utc))

    lost_mins = max(15, int(minutes_lost or 60))
    event_start = day_work_end - timedelta(minutes=lost_mins)

    fixed_event = FixedEvent(
        id=str(uuid.uuid4()),
        title="Unavailable / Reduced Capacity Window",
        start_time=event_start,
        end_time=day_work_end,
        source="manual",
    )
    db.add(fixed_event)
    db.flush()

    return {
        "status": "success",
        "date": target_date.isoformat(),
        "minutes_lost": lost_mins,
        "event_id": fixed_event.id,
        "start_time": event_start.isoformat(),
        "end_time": day_work_end.isoformat(),
    }


def service_rebuild_schedule(
    db: Session,
    start: Optional[datetime] = None,
    horizon_days: int = 7,
) -> Dict[str, Any]:
    """Rebuilds schedule for active tasks via the deterministic scheduler."""
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
        horizon_days=horizon_days,
    )

    # Replace future uncompleted blocks in staging
    db.query(ScheduleBlock).filter(
        ScheduleBlock.is_completed == False,
        ScheduleBlock.start_time >= now,
    ).delete(synchronize_session=False)

    new_blocks = []
    for b in sched_res.blocks:
        new_blocks.append(
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
    db.add_all(new_blocks)

    placed_ids = {b.task_id for b in sched_res.blocks}
    for t in active_tasks:
        if t.id in placed_ids and t.status != "completed":
            t.status = "scheduled"

    db.flush()

    return {
        "status": "success",
        "scheduled_blocks_count": len(sched_res.blocks),
        "unscheduled_tasks_count": len(sched_res.unscheduled_tasks),
        "blocks": [
            {
                "id": b.id,
                "task_id": b.task_id,
                "title": b.title,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "is_at_risk": b.is_at_risk,
            }
            for b in sched_res.blocks
        ],
        "unscheduled_tasks": [
            {
                "task_id": u.task_id,
                "title": u.title,
                "reason": u.reason,
                "remaining_minutes": u.remaining_minutes,
                "deadline": u.deadline.isoformat() if u.deadline else None,
                "at_risk": u.at_risk,
            }
            for u in sched_res.unscheduled_tasks
        ],
    }


# ---------------------------------------------------------------------------
# Tool Dispatcher with Safety Enforcement
# ---------------------------------------------------------------------------

def execute_agent_tool(
    name: str,
    args: Dict[str, Any],
    db: Session,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Safely executes an agent tool call.
    Enforces safety: agent CANNOT delete tasks under any circumstances.
    """
    tool_name = (name or "").strip().lower()

    # Safety constraint: rejection of deletion operations
    if "delete" in tool_name or "remove" in tool_name or "drop_task" in tool_name:
        return {
            "error": "Safety policy violation: The agent cannot delete tasks, only defer or flag them."
        }

    if tool_name == "get_plan":
        range_val = args.get("range", "today")
        return service_get_plan(db=db, range_val=range_val, reference_time=reference_time)

    elif tool_name == "move_task":
        task_id = args.get("task_id", "")
        new_start = args.get("new_start", "")
        return service_move_task(db=db, task_id=task_id, new_start=new_start, reference_time=reference_time)

    elif tool_name == "split_task":
        task_id = args.get("task_id", "")
        parts = args.get("parts", 2)
        return service_split_task(db=db, task_id=task_id, parts=parts)

    elif tool_name == "defer_task":
        task_id = args.get("task_id", "")
        new_deadline = args.get("new_deadline", "")
        return service_defer_task(db=db, task_id=task_id, new_deadline=new_deadline, reference_time=reference_time)

    elif tool_name == "set_priority":
        task_id = args.get("task_id", "")
        importance = args.get("importance", 3)
        return service_set_priority(db=db, task_id=task_id, importance=importance)

    elif tool_name == "add_task":
        title = args.get("title", "")
        est_minutes = args.get("est_minutes", 60)
        importance = args.get("importance", 3)
        deadline = args.get("deadline")
        category = args.get("category")
        description = args.get("description")
        return service_add_task(
            db=db,
            title=title,
            est_minutes=est_minutes,
            importance=importance,
            deadline=deadline,
            category=category,
            description=description,
            reference_time=reference_time,
        )

    elif tool_name == "mark_done":
        task_id = args.get("task_id", "")
        return service_mark_done(db=db, task_id=task_id)

    elif tool_name == "reduce_available_time":
        date_val = args.get("date", "today")
        minutes_lost = args.get("minutes_lost", 180)
        return service_reduce_available_time(
            db=db,
            date_val=date_val,
            minutes_lost=minutes_lost,
            reference_time=reference_time,
        )

    elif tool_name == "rebuild_schedule":
        horizon_days = args.get("horizon_days", 7)
        return service_rebuild_schedule(db=db, start=reference_time, horizon_days=horizon_days)

    else:
        return {"error": f"Unknown tool: '{name}'"}


# ---------------------------------------------------------------------------
# Declarations for Gemini Function Calling
# ---------------------------------------------------------------------------

AGENT_TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_plan",
        description="Get current schedule blocks and active tasks for a given date range (e.g. 'today', 'tomorrow', 'this_week', '7_days').",
        parameters={
            "type": "object",
            "properties": {
                "range": {
                    "type": "string",
                    "description": "Date range or descriptor, e.g. 'today', 'tomorrow', 'this_week', '7_days', or 'YYYY-MM-DD'.",
                }
            },
            "required": ["range"],
        },
    ),
    types.FunctionDeclaration(
        name="move_task",
        description="Move a scheduled task block to start at a specified date and time.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The unique ID or title of the task to move."},
                "new_start": {"type": "string", "description": "The new start timestamp (ISO format, or date/time string)."},
            },
            "required": ["task_id", "new_start"],
        },
    ),
    types.FunctionDeclaration(
        name="split_task",
        description="Enable splitting for a large task into smaller chunks across multiple days or slots.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The unique ID or title of the task to split."},
                "parts": {"type": "integer", "description": "Number of chunks or parts (default 2)."},
            },
            "required": ["task_id", "parts"],
        },
    ),
    types.FunctionDeclaration(
        name="defer_task",
        description="Defer or postpone a task by updating its target deadline to a later date.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The unique ID or title of the task to defer."},
                "new_deadline": {"type": "string", "description": "The new deadline date/time (e.g. 'Friday', 'tomorrow', '2026-10-30T17:00:00Z')."},
            },
            "required": ["task_id", "new_deadline"],
        },
    ),
    types.FunctionDeclaration(
        name="set_priority",
        description="Set the importance or priority of a task (1-5, where 5 is urgent/top priority, 1 is low).",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The unique ID or title of the task."},
                "importance": {"type": "integer", "description": "Importance level 1 (lowest) to 5 (urgent/top priority)."},
            },
            "required": ["task_id", "importance"],
        },
    ),
    types.FunctionDeclaration(
        name="add_task",
        description="Create and add a new task to be scheduled. Safety: tasks cannot be deleted once created.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title."},
                "est_minutes": {"type": "integer", "description": "Estimated duration in minutes."},
                "importance": {"type": "integer", "description": "Importance level 1-5 (default 3)."},
                "deadline": {"type": "string", "description": "Optional deadline (ISO timestamp or date)."},
                "category": {"type": "string", "description": "Category name (e.g. 'work', 'study', 'health')."},
            },
            "required": ["title", "est_minutes"],
        },
    ),
    types.FunctionDeclaration(
        name="mark_done",
        description="Mark a task and its associated schedule blocks as completed.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The unique ID or title of the task."},
            },
            "required": ["task_id"],
        },
    ),
    types.FunctionDeclaration(
        name="reduce_available_time",
        description="Reduce available working hours on a date due to reduced capacity, fatigue, or appointments.",
        parameters={
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to reduce capacity on (e.g. 'today', 'tomorrow', 'YYYY-MM-DD')."},
                "minutes_lost": {"type": "integer", "description": "Number of minutes of working capacity lost."},
            },
            "required": ["date", "minutes_lost"],
        },
    ),
    types.FunctionDeclaration(
        name="rebuild_schedule",
        description="Invoke the deterministic scheduler to recompute and place schedule blocks for all active tasks.",
        parameters={
            "type": "object",
            "properties": {
                "horizon_days": {"type": "integer", "description": "Scheduling horizon in days (default 7)."}
            },
        },
    ),
]

AGENT_GEMINI_TOOL = types.Tool(function_declarations=AGENT_TOOL_DECLARATIONS)
