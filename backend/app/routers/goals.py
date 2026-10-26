from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Goal, Task
from app.schemas.goal_decomposition import (
    GoalDecomposeRequest,
    GoalDecomposeResponse,
    GoalSaveRequest,
    GoalSaveResponse,
    GoalDecomposition,
    TaskDecomposition,
    GoalDecompositionLLMResponse,
)
from app.services.goal_decomposition import (
    AbsurdOutputError,
    decompose_goals_with_gemini,
    validate_decomposition,
)

router = APIRouter(prefix="/goals", tags=["Goal Decomposition & Planning"])


def _importance_to_priority(importance: int) -> str:
    """Maps 1-5 importance score to system task priority."""
    if importance >= 5:
        return "urgent_important"
    elif importance >= 4:
        return "important"
    elif importance >= 3:
        return "normal"
    return "low"


@router.post(
    "/decompose",
    response_model=GoalDecomposeResponse,
    summary="Decompose natural-language goal into structured plan",
    description="Uses Gemini API structured output (gemini-3.8-flash) to break high-level goal statements into goals and tasks with duration, importance, deadlines, dependencies, and rationale. Asks clarifying questions if deadline or scope is missing, and validates against absurd outputs (>8h tasks, cycles).",
)
def decompose_goal(
    request: GoalDecomposeRequest,
    db: Session = Depends(get_db),
):
    prompt = request.get_prompt()
    if not prompt:
        ref_time = request.reference_time or datetime.now(timezone.utc)
        return GoalDecomposeResponse(
            status="clarification_needed",
            message="Goal prompt is required. Please provide a description of your goal, timeframe, and deliverables.",
            needs_clarification=True,
            clarifying_questions=[
                "What is your target deadline or timeframe for this goal?",
                "What specific topics or deliverables are you looking to achieve?",
            ],
            goals=[],
            can_save=False,
            reference_time=ref_time,
        )

    ref_time = request.reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    try:
        llm_result: GoalDecompositionLLMResponse = decompose_goals_with_gemini(
            prompt=prompt,
            reference_time=ref_time,
            demo_mode=getattr(request, "demo_mode", False) or False,
        )

        if llm_result.needs_clarification and llm_result.clarifying_questions:
            return GoalDecomposeResponse(
                status="clarification_needed",
                message="Clarifying questions needed before generating full schedule.",
                needs_clarification=True,
                clarifying_questions=llm_result.clarifying_questions,
                goals=llm_result.goals,
                can_save=False,
                reference_time=ref_time,
            )

        return GoalDecomposeResponse(
            status="success",
            message=f"Successfully decomposed into {len(llm_result.goals)} goal(s). Review and edit tasks before saving.",
            needs_clarification=False,
            clarifying_questions=[],
            goals=llm_result.goals,
            can_save=True,
            reference_time=ref_time,
        )

    except AbsurdOutputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plan validation rejected absurd output: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Goal decomposition failed: {str(e)}",
        )


@router.post(
    "/save",
    response_model=GoalSaveResponse,
    summary="Save reviewed and edited goals to database",
    description="Validates reviewed/edited goals and tasks against business rules (no circular dependencies, task duration <= 8 hours), then saves them to the database.",
)
@router.post(
    "/decompose/save",
    response_model=GoalSaveResponse,
    include_in_schema=False,
)
def save_decomposed_goals(
    request: GoalSaveRequest,
    db: Session = Depends(get_db),
):
    try:
        # 1. Validate the user-reviewed payload against business rules
        mock_llm_response = GoalDecompositionLLMResponse(
            needs_clarification=False,
            clarifying_questions=[],
            goals=request.goals,
        )
        validate_decomposition(mock_llm_response)

        saved_goal_ids: List[str] = []
        saved_task_ids: List[str] = []

        now = datetime.now(timezone.utc)

        # 2. Persist goals and tasks in database
        for goal_data in request.goals:
            target_dt = None
            if goal_data.target_date:
                try:
                    target_dt = datetime.fromisoformat(goal_data.target_date)
                    if target_dt.tzinfo is None:
                        target_dt = target_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            db_goal = Goal(
                id=goal_data.id or str(uuid.uuid4()),
                title=goal_data.title,
                description=goal_data.description,
                target_date=target_dt,
                status="in_progress",
            )
            db.add(db_goal)
            db.flush()
            saved_goal_ids.append(db_goal.id)

            # Map created task instances to wire up dependencies
            created_tasks: List[Task] = []
            for task_data in goal_data.tasks:
                task_deadline = None
                if task_data.deadline:
                    try:
                        task_deadline = datetime.fromisoformat(task_data.deadline)
                        if task_deadline.tzinfo is None:
                            task_deadline = task_deadline.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                description_lines = []
                if task_data.category:
                    description_lines.append(f"Category: {task_data.category}")
                if task_data.rationale:
                    description_lines.append(f"Rationale: {task_data.rationale}")

                db_task = Task(
                    id=task_data.id or str(uuid.uuid4()),
                    goal_id=db_goal.id,
                    title=task_data.title,
                    description="\n".join(description_lines) if description_lines else None,
                    estimated_duration_minutes=task_data.est_minutes,
                    remaining_duration_minutes=task_data.est_minutes,
                    priority=_importance_to_priority(task_data.importance),
                    deadline=task_deadline,
                    is_splittable=task_data.est_minutes >= 60,
                    min_chunk_minutes=30 if task_data.est_minutes >= 60 else task_data.est_minutes,
                    status="pending",
                )
                db.add(db_task)
                created_tasks.append(db_task)

            db.flush()
            saved_task_ids.extend([t.id for t in created_tasks])

        db.commit()

        return GoalSaveResponse(
            status="success",
            message=f"Successfully saved {len(saved_goal_ids)} goal(s) and {len(saved_task_ids)} task(s).",
            saved_goals_count=len(saved_goal_ids),
            saved_tasks_count=len(saved_task_ids),
            goal_ids=saved_goal_ids,
            task_ids=saved_task_ids,
        )

    except AbsurdOutputError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error on reviewed goals: {str(e)}",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save goals: {str(e)}",
        )
