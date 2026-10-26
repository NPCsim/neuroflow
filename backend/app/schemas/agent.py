from __future__ import annotations

from typing import Any, List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AgentCommandRequest(BaseModel):
    message: Optional[str] = Field(None, description="Natural language prompt or instruction from the user")
    command: Optional[str] = Field(None, description="Alias for message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation context identifier")
    reference_time: Optional[datetime] = Field(None, description="Current simulated time (UTC), defaults to now")
    demo_mode: Optional[bool] = Field(default=False, description="Enable deterministic scripted demo mode")

    def get_prompt(self) -> str:
        return (self.message or self.command or "").strip()


class PlanDiffItemMoved(BaseModel):
    task_id: str
    title: str
    old_start: Optional[str] = None
    new_start: str
    old_end: Optional[str] = None
    new_end: str
    diff_minutes: Optional[int] = None


class PlanDiffItemDeferred(BaseModel):
    task_id: str
    title: str
    old_deadline: Optional[str] = None
    new_deadline: Optional[str] = None
    reason: str


class PlanDiffItemDropped(BaseModel):
    task_id: str
    title: str
    remaining_minutes: int
    reason: str


class PlanDiffItemAtRisk(BaseModel):
    task_id: str
    title: str
    deadline: Optional[str] = None
    scheduled_end: Optional[str] = None
    reason: str


class PlanDiff(BaseModel):
    moved: List[PlanDiffItemMoved] = Field(default_factory=list)
    deferred: List[PlanDiffItemDeferred] = Field(default_factory=list)
    dropped: List[PlanDiffItemDropped] = Field(default_factory=list)
    at_risk: List[PlanDiffItemAtRisk] = Field(default_factory=list, alias="at_risk")

    model_config = ConfigDict(populate_by_name=True)


class AgentCommandResponse(BaseModel):
    summary: str = Field(..., description="Agent natural language summary of staged modifications")
    diff: Dict[str, Any] = Field(..., description="Plan diff categorizing moved, deferred, dropped, and at-risk tasks")
    snapshot_id: str = Field(..., description="Unique ID for the staged PlanProposal snapshot")
    status: str = Field("staged", description="Status of command staging: staged")
    steps_executed: int = Field(0, description="Number of agent tool loop iterations executed")


class AgentApplyResponse(BaseModel):
    status: str = Field("applied", description="Status after applying snapshot")
    snapshot_id: str = Field(..., description="Snapshot ID applied")
    message: str = Field(..., description="Outcome message")
    applied_at: datetime = Field(..., description="Timestamp of when plan was committed")
    summary: Optional[str] = None
    diff: Optional[Dict[str, Any]] = None


class AgentUndoResponse(BaseModel):
    status: str = Field(..., description="reverted if previously applied, or rejected if draft was discarded")
    snapshot_id: str = Field(..., description="Snapshot ID that was undone/reverted")
    message: str = Field(..., description="Outcome message")
    previous_status: str = Field(..., description="Status prior to undo")


class AgentUndoRequest(BaseModel):
    snapshot_id: Optional[str] = Field(None, description="Optional snapshot ID to undo. Defaults to most recent.")

