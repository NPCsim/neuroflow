from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlanProposal
from app.schemas.agent import (
    AgentCommandRequest,
    AgentCommandResponse,
    AgentApplyResponse,
    AgentUndoResponse,
    AgentUndoRequest,
)
from app.services.agent_service import (
    run_agent_command,
    apply_plan_snapshot,
    undo_plan_snapshot,
)

router = APIRouter(prefix="/agent", tags=["AI Agent Copilot"])


@router.post(
    "/command",
    response_model=AgentCommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute agent natural language scheduling command via Gemini function calling",
    description=(
        "Executes agent tool calling loop (max 6 steps) to adjust tasks and schedule. "
        "Changes are staged in a nested transaction without committing, computing a plan diff "
        "(moved, deferred, dropped, at-risk) and saving a reviewable PlanProposal snapshot."
    ),
)
def handle_agent_command(
    request: AgentCommandRequest,
    db: Session = Depends(get_db),
):
    prompt = request.get_prompt()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A non-empty 'message' or 'command' is required.",
        )

    try:
        result = run_agent_command(
            db=db,
            message=prompt,
            conversation_id=request.conversation_id,
            reference_time=request.reference_time,
            demo_mode=getattr(request, "demo_mode", False) or False,
        )
        return AgentCommandResponse(
            summary=result["summary"],
            diff=result["diff"],
            snapshot_id=result["snapshot_id"],
            status=result.get("status", "staged"),
            steps_executed=result.get("steps_executed", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent command execution failed: {str(e)}",
        )


@router.post(
    "/apply/{snapshot_id}",
    response_model=AgentApplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply and commit a staged plan snapshot to the active schedule",
    description="Applies the staged task modifications, schedule blocks, and constraints from PlanProposal to the database.",
)
def handle_agent_apply(
    snapshot_id: str,
    db: Session = Depends(get_db),
):
    try:
        res = apply_plan_snapshot(db=db, snapshot_id=snapshot_id)
        return AgentApplyResponse(
            status=res["status"],
            snapshot_id=res["snapshot_id"],
            message=res["message"],
            applied_at=res["applied_at"],
            summary=res.get("summary"),
            diff=res.get("diff"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply plan snapshot: {str(e)}",
        )


@router.post(
    "/undo/{snapshot_id}",
    response_model=AgentUndoResponse,
    status_code=status.HTTP_200_OK,
    summary="Undo or revert a plan snapshot",
    description="Discards a pending draft proposal or reverts an approved plan back to its baseline snapshot_before state.",
)
def handle_agent_undo(
    snapshot_id: str,
    db: Session = Depends(get_db),
):
    try:
        res = undo_plan_snapshot(db=db, snapshot_id=snapshot_id)
        return AgentUndoResponse(
            status=res["status"],
            snapshot_id=res["snapshot_id"],
            message=res["message"],
            previous_status=res.get("previous_status", "unknown"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to undo plan snapshot: {str(e)}",
        )


@router.post(
    "/undo",
    response_model=AgentUndoResponse,
    status_code=status.HTTP_200_OK,
    summary="Undo or revert the latest or specified plan snapshot",
    description="Reverts the most recently applied proposal or the snapshot specified in the request body.",
)
def handle_agent_undo_latest(
    request: Optional[AgentUndoRequest] = None,
    db: Session = Depends(get_db),
):
    snapshot_id = request.snapshot_id if request else None
    if not snapshot_id:
        latest = (
            db.query(PlanProposal)
            .filter(PlanProposal.status.in_(["approved", "applied", "draft_pending"]))
            .order_by(PlanProposal.created_at.desc())
            .first()
        )
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No applied or pending plan proposals found to undo.",
            )
        snapshot_id = latest.id

    try:
        res = undo_plan_snapshot(db=db, snapshot_id=snapshot_id)
        return AgentUndoResponse(
            status=res["status"],
            snapshot_id=res["snapshot_id"],
            message=res["message"],
            previous_status=res.get("previous_status", "unknown"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to undo plan snapshot: {str(e)}",
        )

