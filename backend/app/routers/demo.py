from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Goal, Task, FixedEvent, ScheduleBlock
from app.seed import seed_database, FIXED_DEMO_NOW
from app.routers.workload import rollover_schedule
from app.schemas.feasibility import ScheduleRolloverRequest, ScheduleRolloverResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Mode & Simulation"])


class DemoResetRequest(BaseModel):
    fixed_now: Optional[datetime] = Field(
        default=None,
        description="Optional fixed anchor time (defaults to 2026-10-26T09:00:00Z)",
    )


class DemoResetResponse(BaseModel):
    status: str = "success"
    message: str
    fixed_now: datetime
    goals_count: int
    tasks_count: int
    fixed_events_count: int
    blocks_count: int


class ScriptedCommandInfo(BaseModel):
    command: str
    description: str
    tool_action: str


class DemoStatusResponse(BaseModel):
    demo_mode: bool = True
    fixed_now: datetime
    end_of_day: datetime
    scripted_commands: List[ScriptedCommandInfo]
    scripted_goal: str


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    summary="One-click reset to seeded workspace at fixed anchor time",
    description="Clears and re-seeds demo goals, tasks, fixed events, and schedule blocks anchored at fixed now (2026-10-26T09:00:00Z) so demo views look identical every time.",
)
def reset_demo_workspace(
    request: Optional[DemoResetRequest] = None,
    db: Session = Depends(get_db),
):
    anchor_time = (request.fixed_now if request and request.fixed_now else None) or FIXED_DEMO_NOW
    if anchor_time.tzinfo is None:
        anchor_time = anchor_time.replace(tzinfo=timezone.utc)

    try:
        seed_database(fixed_now=anchor_time, db=db)
        goals_cnt = db.query(Goal).count()
        tasks_cnt = db.query(Task).count()
        events_cnt = db.query(FixedEvent).count()
        blocks_cnt = db.query(ScheduleBlock).count()

        return DemoResetResponse(
            status="success",
            message=f"Demo workspace seeded at fixed anchor time {anchor_time.isoformat()}",
            fixed_now=anchor_time,
            goals_count=goals_cnt,
            tasks_count=tasks_cnt,
            fixed_events_count=events_cnt,
            blocks_count=blocks_cnt,
        )
    except Exception as e:
        logger.error(f"Error resetting demo workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset demo workspace: {str(e)}",
        )


@router.post(
    "/simulate-end-of-day",
    response_model=ScheduleRolloverResponse,
    summary="Simulate end of working day and trigger rollover",
    description="Simulates advancing time to end-of-day (17:00 UTC), marking past uncompleted blocks as missed, incrementing carryover counts, flagging stuck tasks (3+ carryovers), and rescheduling remaining work.",
)
def simulate_end_of_day(
    db: Session = Depends(get_db),
):
    end_of_day = datetime(2026, 10, 26, 17, 0, 0, tzinfo=timezone.utc)
    try:
        rollover_req = ScheduleRolloverRequest(
            horizon_days=7,
            now=end_of_day,
            current_time=end_of_day,
        )
        return rollover_schedule(request=rollover_req, db=db)
    except Exception as e:
        logger.error(f"Error simulating end of day: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulate end of day failed: {str(e)}",
        )


@router.get(
    "/status",
    response_model=DemoStatusResponse,
    summary="Get demo mode configuration and pre-cached commands",
)
def get_demo_status():
    anchor = FIXED_DEMO_NOW
    end_of_day = datetime(2026, 10, 26, 17, 0, 0, tzinfo=timezone.utc)
    return DemoStatusResponse(
        demo_mode=True,
        fixed_now=anchor,
        end_of_day=end_of_day,
        scripted_commands=[
            ScriptedCommandInfo(
                command="I only have 3 hours today",
                description="Reduces today's capacity by 300 minutes, staging overflow work to subsequent days.",
                tool_action="reduce_available_time(date='today', minutes_lost=300)",
            ),
            ScriptedCommandInfo(
                command="Something urgent came up, defer non-urgent tasks",
                description="Inserts a 60-minute urgent priority task and rebalances the schedule around it.",
                tool_action="add_task(title='Urgent Problem Resolution', est_minutes=60, importance=5)",
            ),
            ScriptedCommandInfo(
                command="Make tomorrow lighter by shifting heavy tasks",
                description="Reduces tomorrow's capacity by 240 minutes, shifting focus blocks later in the week.",
                tool_action="reduce_available_time(date='tomorrow', minutes_lost=240)",
            ),
        ],
        scripted_goal="Prepare for my DBMS exam in 10 days and finish my hackathon project",
    )
