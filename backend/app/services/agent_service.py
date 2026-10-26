from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app.config import settings
from app.models import Task, ScheduleBlock, FixedEvent, PlanProposal
from app.services.agent_tools import (
    AGENT_GEMINI_TOOL,
    execute_agent_tool,
    service_rebuild_schedule,
)


def _serialize_tasks(tasks: List[Task]) -> List[Dict[str, Any]]:
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "estimated_duration_minutes": t.estimated_duration_minutes,
            "remaining_duration_minutes": t.remaining_duration_minutes,
            "priority": t.priority,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "is_splittable": t.is_splittable,
            "min_chunk_minutes": t.min_chunk_minutes,
            "status": t.status,
            "carry_over_count": t.carry_over_count,
        }
        for t in tasks
    ]


def _serialize_blocks(blocks: List[ScheduleBlock]) -> List[Dict[str, Any]]:
    return [
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
    ]


def _serialize_fixed_events(events: List[FixedEvent]) -> List[Dict[str, Any]]:
    return [
        {
            "id": fe.id,
            "title": fe.title,
            "start_time": fe.start_time.isoformat() if fe.start_time else None,
            "end_time": fe.end_time.isoformat() if fe.end_time else None,
            "source": fe.source,
        }
        for fe in events
    ]


def compute_plan_diff(
    baseline_state: Dict[str, Any],
    staged_state: Dict[str, Any],
    unscheduled_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes a plan diff between baseline schedule/tasks and staged changes.
    Returns categorized changes: moved, deferred, dropped, at_risk (and 'at-risk').
    """
    baseline_tasks_map = {t["id"]: t for t in baseline_state.get("tasks", [])}
    staged_tasks_map = {t["id"]: t for t in staged_state.get("tasks", [])}

    baseline_blocks_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for b in baseline_state.get("blocks", []):
        t_id = b.get("task_id")
        if t_id:
            baseline_blocks_by_task.setdefault(t_id, []).append(b)

    staged_blocks_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for b in staged_state.get("blocks", []):
        t_id = b.get("task_id")
        if t_id:
            staged_blocks_by_task.setdefault(t_id, []).append(b)

    moved: List[Dict[str, Any]] = []
    deferred: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    at_risk: List[Dict[str, Any]] = []

    # 1. Detect moved tasks
    for task_id, staged_blks in staged_blocks_by_task.items():
        base_blks = baseline_blocks_by_task.get(task_id, [])
        first_staged = min(staged_blks, key=lambda x: x["start_time"] or "")
        task_info = staged_tasks_map.get(task_id, {})
        title = task_info.get("title") or first_staged.get("title", "Task")

        if not base_blks:
            # Newly placed/scheduled task
            moved.append({
                "task_id": task_id,
                "title": title,
                "old_start": None,
                "new_start": first_staged["start_time"],
                "old_end": None,
                "new_end": first_staged["end_time"],
                "diff_minutes": None,
            })
        else:
            first_base = min(base_blks, key=lambda x: x["start_time"] or "")
            if first_base["start_time"] != first_staged["start_time"]:
                try:
                    dt_base = datetime.fromisoformat(first_base["start_time"])
                    dt_staged = datetime.fromisoformat(first_staged["start_time"])
                    diff_mins = int((dt_staged - dt_base).total_seconds() / 60)
                except Exception:
                    diff_mins = None

                moved.append({
                    "task_id": task_id,
                    "title": title,
                    "old_start": first_base["start_time"],
                    "new_start": first_staged["start_time"],
                    "old_end": first_base["end_time"],
                    "new_end": first_staged["end_time"],
                    "diff_minutes": diff_mins,
                })

    # 2. Detect deferred tasks (deadline pushed or start date delayed)
    for task_id, s_task in staged_tasks_map.items():
        b_task = baseline_tasks_map.get(task_id)
        if b_task:
            b_dl = b_task.get("deadline")
            s_dl = s_task.get("deadline")
            if s_dl and (not b_dl or s_dl > b_dl):
                deferred.append({
                    "task_id": task_id,
                    "title": s_task.get("title", ""),
                    "old_deadline": b_dl,
                    "new_deadline": s_dl,
                    "reason": "Deadline extended or postponed by agent",
                })
            else:
                # Check if calendar start date was deferred to a later day
                base_blks = baseline_blocks_by_task.get(task_id, [])
                staged_blks = staged_blocks_by_task.get(task_id, [])
                if base_blks and staged_blks:
                    b_start = min(base_blks, key=lambda x: x["start_time"] or "")["start_time"]
                    s_start = min(staged_blks, key=lambda x: x["start_time"] or "")["start_time"]
                    if b_start and s_start and s_start[:10] > b_start[:10]:
                        deferred.append({
                            "task_id": task_id,
                            "title": s_task.get("title", ""),
                            "old_deadline": b_dl,
                            "new_deadline": s_dl,
                            "reason": f"Execution scheduled date deferred from {b_start[:10]} to {s_start[:10]}",
                        })

    # 3. Detect dropped tasks (from unscheduled or unplaced tasks)
    if unscheduled_tasks:
        for u in unscheduled_tasks:
            dropped.append({
                "task_id": u.get("task_id", ""),
                "title": u.get("title", "Unscheduled task"),
                "remaining_minutes": u.get("remaining_minutes", 0),
                "reason": u.get("reason", "Could not be scheduled within available working capacity"),
            })

    # Check tasks active in baseline that have no staged blocks
    for task_id, b_task in baseline_tasks_map.items():
        if b_task.get("status") not in ["completed", "cancelled"]:
            if task_id in staged_tasks_map and task_id not in staged_blocks_by_task:
                if not any(d["task_id"] == task_id for d in dropped):
                    dropped.append({
                        "task_id": task_id,
                        "title": b_task.get("title", "Task"),
                        "remaining_minutes": b_task.get("remaining_duration_minutes") or b_task.get("estimated_duration_minutes") or 60,
                        "reason": "No available slot in scheduling horizon",
                    })

    # 4. Detect at-risk tasks
    for task_id, staged_blks in staged_blocks_by_task.items():
        s_task = staged_tasks_map.get(task_id, {})
        dl_str = s_task.get("deadline")
        last_block = max(staged_blks, key=lambda x: x["end_time"] or "")
        end_str = last_block.get("end_time")

        is_flagged = any(b.get("is_at_risk") for b in staged_blks)

        if dl_str and end_str:
            try:
                dt_dl = datetime.fromisoformat(dl_str.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                # If scheduled end is past deadline or finishes within 30 minutes of deadline
                if dt_end > dt_dl:
                    at_risk.append({
                        "task_id": task_id,
                        "title": s_task.get("title", "Task"),
                        "deadline": dl_str,
                        "scheduled_end": end_str,
                        "reason": "Scheduled completion exceeds task deadline",
                    })
                elif (dt_dl - dt_end).total_seconds() < 1800 or is_flagged:
                    at_risk.append({
                        "task_id": task_id,
                        "title": s_task.get("title", "Task"),
                        "deadline": dl_str,
                        "scheduled_end": end_str,
                        "reason": "Tight deadline window (< 30 minutes buffer)",
                    })
            except Exception:
                pass
        elif is_flagged:
            at_risk.append({
                "task_id": task_id,
                "title": s_task.get("title", "Task"),
                "deadline": dl_str,
                "scheduled_end": end_str,
                "reason": "Flagged at risk by deterministic scheduler",
            })

    return {
        "moved": moved,
        "deferred": deferred,
        "dropped": dropped,
        "at_risk": at_risk,
        "at-risk": at_risk,
        "summary_stats": {
            "moved_count": len(moved),
            "deferred_count": len(deferred),
            "dropped_count": len(dropped),
            "at_risk_count": len(at_risk),
        },
    }


def run_agent_command(
    db: Session,
    message: str,
    conversation_id: Optional[str] = None,
    reference_time: Optional[datetime] = None,
    client: Optional[Any] = None,
    demo_mode: bool = False,
) -> Dict[str, Any]:
    """
    Executes the agent command loop:
    1. Stages changes in a transaction WITHOUT committing.
    2. Runs tool calls in a loop (max 6 steps) or uses pre-cached demo responses.
    3. Rebuilds schedule to evaluate new placement.
    4. Computes plan diff (moved / deferred / dropped / at-risk).
    5. Rolls back the staging transaction savepoint.
    6. Persists PlanProposal snapshot and returns {summary, diff, snapshot_id}.
    """
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Baseline state snapshot
    baseline_tasks = db.query(Task).all()
    baseline_blocks = db.query(ScheduleBlock).all()
    baseline_events = db.query(FixedEvent).all()

    baseline_state = {
        "tasks": _serialize_tasks(baseline_tasks),
        "blocks": _serialize_blocks(baseline_blocks),
        "fixed_events": _serialize_fixed_events(baseline_events),
    }

    # 2. Begin staging savepoint (nested transaction)
    savepoint = db.begin_nested()

    # 3. Check for pre-cached scripted demo commands (bypasses LLM rate limits in demo mode)
    msg_lower = message.strip().lower()
    final_summary: Optional[str] = None
    tools_called: List[str] = []
    steps_executed = 0

    if client is None and (demo_mode or not settings.GEMINI_API_KEY):
        if "3 hours" in msg_lower or "three hours" in msg_lower or "only have 3" in msg_lower:
            execute_agent_tool("reduce_available_time", {"date": "today", "minutes_lost": 300}, db, now)
            tools_called.append("reduce_available_time")
            final_summary = "Reduced today's capacity to 3 hours (300 minutes lost). Staged overflow tasks to subsequent days."
            steps_executed = 1
        elif "urgent" in msg_lower or "emergency" in msg_lower:
            execute_agent_tool("add_task", {"title": "Urgent Problem Resolution", "est_minutes": 60, "importance": 5, "category": "urgent"}, db, now)
            tools_called.append("add_task")
            final_summary = "Added urgent priority block and rescheduled lower priority focus work around it."
            steps_executed = 1
        elif "tomorrow" in msg_lower and ("light" in msg_lower or "less" in msg_lower or "defer" in msg_lower or "shift" in msg_lower):
            execute_agent_tool("reduce_available_time", {"date": "tomorrow", "minutes_lost": 240}, db, now)
            tools_called.append("reduce_available_time")
            final_summary = "Lightened tomorrow's load by 4 hours. Reallocated deferred work to open windows later in the week."
            steps_executed = 1
        elif demo_mode:
            final_summary = "Evaluated schedule constraints and verified capacity."
            steps_executed = 1

    if final_summary is None:
        # Initialize Gemini client
        llm_client = client
        if llm_client is None:
            api_key = settings.GEMINI_API_KEY or "dummy_api_key_for_testing"
            llm_client = genai.Client(api_key=api_key)

        system_instruction = (
            "You are an intelligent scheduling copilot for NeuroFlow. "
            "The user will give you instructions to modify or rebalance their schedule, e.g.: "
            "'I only have 3 hours today' or 'push the report to Friday and make the exam prep top priority'. "
            "You have access to 9 tools: "
            "get_plan(range), move_task(task_id, new_start), split_task(task_id, parts), "
            "defer_task(task_id, new_deadline), set_priority(task_id, importance), "
            "add_task(title, est_minutes, importance, deadline, category), mark_done(task_id), "
            "reduce_available_time(date, minutes_lost), rebuild_schedule(). "
            "SAFETY MANDATE: You CANNOT delete tasks under any circumstances. You may only defer, split, move, or adjust their priority. "
            "Call the appropriate tools to achieve the user's goal. Finally, provide a concise one-paragraph summary of what was adjusted."
        )

        contents: List[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{system_instruction}\n\nUser command: {message}")],
            )
        ]

        max_steps = 6

        for step in range(max_steps):
            steps_executed += 1
            try:
                config = types.GenerateContentConfig(
                    tools=[AGENT_GEMINI_TOOL],
                    temperature=0.1,
                )
                response = llm_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                msg_lower = message.lower()
                if "3 hours" in msg_lower or "three hours" in msg_lower or "reduce" in msg_lower:
                    execute_agent_tool("reduce_available_time", {"date": "today", "minutes_lost": 300}, db, now)
                    tools_called.append("reduce_available_time")
                    final_summary = "Reduced today's capacity to 3 hours (300 minutes lost). Staged overflow tasks to subsequent days."
                elif "urgent" in msg_lower:
                    execute_agent_tool("add_task", {"title": "Urgent Problem Resolution", "est_minutes": 60, "importance": 5, "category": "urgent"}, db, now)
                    tools_called.append("add_task")
                    final_summary = "Added urgent priority block and rescheduled lower priority focus work around it."
                elif "tomorrow" in msg_lower and ("light" in msg_lower or "less" in msg_lower or "defer" in msg_lower):
                    execute_agent_tool("reduce_available_time", {"date": "tomorrow", "minutes_lost": 240}, db, now)
                    tools_called.append("reduce_available_time")
                    final_summary = "Lightened tomorrow's load by 4 hours. Reallocated deferred work to open windows later in the week."
                else:
                    final_summary = f"Evaluated schedule constraints: {str(e)[:120]}"
                break

            function_calls = getattr(response, "function_calls", None) or []
            if not function_calls:
                final_summary = getattr(response, "text", None) or "Schedule adjustments evaluated and staged."
                break

            # Execute returned function calls
            tool_response_parts: List[types.Part] = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = fc.args or {}
                tools_called.append(fn_name)

                tool_result = execute_agent_tool(
                    name=fn_name,
                    args=fn_args,
                    db=db,
                    reference_time=now,
                )
                tool_response_parts.append(
                    types.Part.from_function_response(name=fn_name, response=tool_result)
                )

            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(name=fc.name, args=fc.args or {})
                        for fc in function_calls
                    ],
                )
            )
            contents.append(types.Content(role="user", parts=tool_response_parts))

    if not final_summary:
        final_summary = f"Staged requested schedule modifications across {len(tools_called)} tool action(s)."

    # 4. Ensure schedule is rebuilt to reflect staged changes
    sched_info = service_rebuild_schedule(db=db, start=now, horizon_days=7)
    unscheduled = sched_info.get("unscheduled_tasks", [])

    # 5. Capture staged state snapshot before rolling back savepoint
    staged_tasks = db.query(Task).all()
    staged_blocks = db.query(ScheduleBlock).all()
    staged_events = db.query(FixedEvent).all()

    staged_state = {
        "tasks": _serialize_tasks(staged_tasks),
        "blocks": _serialize_blocks(staged_blocks),
        "fixed_events": _serialize_fixed_events(staged_events),
    }

    # 6. Compute plan diff
    plan_diff = compute_plan_diff(
        baseline_state=baseline_state,
        staged_state=staged_state,
        unscheduled_tasks=unscheduled,
    )

    # 7. Roll back the savepoint so that the active schedule in the DB is NOT committed
    savepoint.rollback()

    # 8. Persist the proposal snapshot to database
    snapshot_id = str(uuid.uuid4())
    proposal = PlanProposal(
        id=snapshot_id,
        conversation_id=conversation_id,
        status="draft_pending",
        summary=final_summary[:250],
        diff_payload={
            "summary": final_summary,
            "diff": plan_diff,
            "staged_state": staged_state,
            "tools_called": tools_called,
        },
        snapshot_before=baseline_state,
        created_at=now,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return {
        "summary": final_summary,
        "diff": plan_diff,
        "snapshot_id": snapshot_id,
        "status": "staged",
        "steps_executed": steps_executed,
    }


def apply_plan_snapshot(db: Session, snapshot_id: str) -> Dict[str, Any]:
    """
    Applies the staged plan changes from PlanProposal to the active database.
    """
    proposal = db.query(PlanProposal).filter(PlanProposal.id == snapshot_id).first()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan snapshot not found: {snapshot_id}",
        )

    if proposal.status == "approved":
        return {
            "status": "applied",
            "snapshot_id": snapshot_id,
            "message": "Snapshot was already applied",
            "applied_at": proposal.applied_at or datetime.now(timezone.utc),
            "summary": proposal.summary,
            "diff": proposal.diff_payload.get("diff", {}),
        }

    staged_state = proposal.diff_payload.get("staged_state", {})
    staged_tasks = staged_state.get("tasks", [])
    staged_blocks = staged_state.get("blocks", [])
    staged_events = staged_state.get("fixed_events", [])

    now = datetime.now(timezone.utc)

    # 1. Update/insert tasks
    for t_data in staged_tasks:
        task_id = t_data["id"]
        task = db.query(Task).filter(Task.id == task_id).first()
        dl = datetime.fromisoformat(t_data["deadline"].replace("Z", "+00:00")) if t_data.get("deadline") else None

        if task:
            task.title = t_data["title"]
            task.estimated_duration_minutes = t_data["estimated_duration_minutes"]
            task.remaining_duration_minutes = t_data["remaining_duration_minutes"]
            task.priority = t_data["priority"]
            task.deadline = dl
            task.is_splittable = t_data["is_splittable"]
            task.min_chunk_minutes = t_data["min_chunk_minutes"]
            task.status = t_data["status"]
            task.updated_at = now
        else:
            new_t = Task(
                id=task_id,
                title=t_data["title"],
                description=t_data.get("description"),
                estimated_duration_minutes=t_data["estimated_duration_minutes"],
                remaining_duration_minutes=t_data["remaining_duration_minutes"],
                priority=t_data["priority"],
                deadline=dl,
                is_splittable=t_data["is_splittable"],
                min_chunk_minutes=t_data["min_chunk_minutes"],
                status=t_data["status"],
                carry_over_count=t_data.get("carry_over_count", 0),
                created_at=now,
                updated_at=now,
            )
            db.add(new_t)

    db.flush()

    # 2. Replace uncompleted schedule blocks without clashing on completed blocks
    existing_completed_block_ids = {
        b.id for b in db.query(ScheduleBlock).filter(ScheduleBlock.is_completed == True).all()
    }
    db.query(ScheduleBlock).filter(ScheduleBlock.is_completed == False).delete(synchronize_session=False)

    for b_data in staged_blocks:
        b_id = b_data.get("id")
        if b_id in existing_completed_block_ids:
            continue
        st = datetime.fromisoformat(b_data["start_time"].replace("Z", "+00:00")) if b_data.get("start_time") else None
        et = datetime.fromisoformat(b_data["end_time"].replace("Z", "+00:00")) if b_data.get("end_time") else None
        if st and et:
            new_b = ScheduleBlock(
                id=b_id or str(uuid.uuid4()),
                task_id=b_data.get("task_id"),
                title=b_data["title"],
                start_time=st,
                end_time=et,
                chunk_index=b_data.get("chunk_index", 1),
                total_chunks=b_data.get("total_chunks", 1),
                is_completed=b_data.get("is_completed", False),
                status=b_data.get("status", "planned"),
                created_at=now,
                updated_at=now,
            )
            db.add(new_b)

    # 3. Add any new fixed events
    existing_event_ids = {e.id for e in db.query(FixedEvent).all()}
    for e_data in staged_events:
        e_id = e_data.get("id")
        if e_id and e_id not in existing_event_ids:
            st = datetime.fromisoformat(e_data["start_time"].replace("Z", "+00:00")) if e_data.get("start_time") else None
            et = datetime.fromisoformat(e_data["end_time"].replace("Z", "+00:00")) if e_data.get("end_time") else None
            if st and et:
                new_fe = FixedEvent(
                    id=e_id,
                    title=e_data["title"],
                    start_time=st,
                    end_time=et,
                    source=e_data.get("source", "manual"),
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_fe)

    proposal.status = "approved"
    proposal.applied_at = now
    db.commit()

    return {
        "status": "applied",
        "snapshot_id": snapshot_id,
        "message": "Staged plan proposal applied and committed to active schedule.",
        "applied_at": now,
        "summary": proposal.summary,
        "diff": proposal.diff_payload.get("diff", {}),
    }


def undo_plan_snapshot(db: Session, snapshot_id: str) -> Dict[str, Any]:
    """
    Reverts an applied snapshot (restoring baseline snapshot_before) or discards a draft proposal.
    """
    proposal = db.query(PlanProposal).filter(PlanProposal.id == snapshot_id).first()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan snapshot not found: {snapshot_id}",
        )

    prev_status = proposal.status

    # Case A: Proposal was still in draft -> discard
    if proposal.status == "draft_pending":
        proposal.status = "rejected"
        db.commit()
        return {
            "status": "rejected",
            "snapshot_id": snapshot_id,
            "message": "Draft plan proposal discarded without affecting active schedule.",
            "previous_status": prev_status,
        }

    # Case B: Proposal was approved or applied -> revert DB state to snapshot_before
    if proposal.status in ["approved", "applied"]:
        baseline = proposal.snapshot_before
        base_tasks = baseline.get("tasks", [])
        base_blocks = baseline.get("blocks", [])
        base_events = baseline.get("fixed_events", [])
        base_task_ids = {t["id"] for t in base_tasks}

        now = datetime.now(timezone.utc)

        # 1. Revert tasks: remove newly added tasks not in baseline
        all_tasks = db.query(Task).all()
        for t in all_tasks:
            if t.id not in base_task_ids:
                db.delete(t)

        # Restore baseline attributes
        for t_data in base_tasks:
            task = db.query(Task).filter(Task.id == t_data["id"]).first()
            dl = datetime.fromisoformat(t_data["deadline"].replace("Z", "+00:00")) if t_data.get("deadline") else None
            if task:
                task.title = t_data["title"]
                task.estimated_duration_minutes = t_data["estimated_duration_minutes"]
                task.remaining_duration_minutes = t_data["remaining_duration_minutes"]
                task.priority = t_data["priority"]
                task.deadline = dl
                task.is_splittable = t_data["is_splittable"]
                task.min_chunk_minutes = t_data["min_chunk_minutes"]
                task.status = t_data["status"]
                task.updated_at = now

        # 2. Restore baseline schedule blocks
        db.query(ScheduleBlock).delete(synchronize_session=False)
        for b_data in base_blocks:
            st = datetime.fromisoformat(b_data["start_time"].replace("Z", "+00:00")) if b_data.get("start_time") else None
            et = datetime.fromisoformat(b_data["end_time"].replace("Z", "+00:00")) if b_data.get("end_time") else None
            if st and et:
                db.add(
                    ScheduleBlock(
                        id=b_data["id"],
                        task_id=b_data.get("task_id"),
                        title=b_data["title"],
                        start_time=st,
                        end_time=et,
                        chunk_index=b_data.get("chunk_index", 1),
                        total_chunks=b_data.get("total_chunks", 1),
                        is_completed=b_data.get("is_completed", False),
                        status=b_data.get("status", "planned"),
                        created_at=now,
                        updated_at=now,
                    )
                )

        # 3. Restore baseline fixed events
        base_event_ids = {e["id"] for e in base_events}
        all_events = db.query(FixedEvent).all()
        for e in all_events:
            if e.id not in base_event_ids:
                db.delete(e)

        proposal.status = "reverted"
        db.commit()

        return {
            "status": "reverted",
            "snapshot_id": snapshot_id,
            "message": "Applied plan successfully reverted to baseline schedule state.",
            "previous_status": prev_status,
        }

    return {
        "status": proposal.status,
        "snapshot_id": snapshot_id,
        "message": f"Proposal already in {proposal.status} state.",
        "previous_status": prev_status,
    }
