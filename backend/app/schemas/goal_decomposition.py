from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class TaskDecomposition(BaseModel):
    id: Optional[str] = Field(None, description="Temporary or persistent task ID")
    title: str = Field(..., min_length=1, description="Actionable title of the task")
    est_minutes: int = Field(..., description="Estimated duration in minutes (max 8 hours / 480 min)")
    importance: int = Field(..., description="Importance score from 1 (low) to 5 (critical)")
    deadline: Optional[str] = Field(None, description="ISO-8601 deadline for this task, if applicable")
    depends_on: List[int] = Field(default_factory=list, description="0-based indices of prerequisite tasks within this goal")
    category: str = Field(default="general", description="Category tag, e.g. study, engineering, review, design, admin")
    rationale: str = Field(..., description="One-line rationale for why this task is necessary")


class GoalDecomposition(BaseModel):
    id: Optional[str] = Field(None, description="Temporary or persistent goal ID")
    title: str = Field(..., min_length=1, description="Title of the goal")
    description: Optional[str] = Field(None, description="Summary description of the goal")
    target_date: Optional[str] = Field(None, description="Target completion date in ISO-8601 format")
    tasks: List[TaskDecomposition] = Field(default_factory=list, description="List of tasks for this goal")


class GoalDecompositionLLMResponse(BaseModel):
    needs_clarification: bool = Field(default=False, description="True if deadline or scope is missing and clarifying questions are required")
    clarifying_questions: List[str] = Field(default_factory=list, description="Clarifying questions when deadline or scope is missing instead of guessing")
    goals: List[GoalDecomposition] = Field(default_factory=list, description="List of decomposed goals and their tasks")


class GoalDecomposeRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="Natural-language goal prompt, e.g. 'Prepare for my DBMS exam in 10 days and finish my hackathon project'")
    goal: Optional[str] = Field(None, description="Alias for prompt")
    goal_prompt: Optional[str] = Field(None, description="Alias for prompt")
    reference_time: Optional[datetime] = Field(None, description="Reference anchor time for relative deadlines (defaults to UTC now)")
    clarifications: Optional[dict[str, Any]] = Field(None, description="User answers to previous clarifying questions")
    demo_mode: Optional[bool] = Field(default=False, description="Enable scripted demo mode")

    def get_prompt(self) -> str:
        p = self.prompt or self.goal or self.goal_prompt or ""
        return p.strip()


class GoalDecomposeResponse(BaseModel):
    status: str = "success"  # "success" or "clarification_needed"
    message: str
    needs_clarification: bool = False
    clarifying_questions: List[str] = Field(default_factory=list)
    goals: List[GoalDecomposition] = Field(default_factory=list)
    can_save: bool = True
    reference_time: datetime


class GoalSaveRequest(BaseModel):
    goals: List[GoalDecomposition] = Field(..., min_length=1, description="Reviewed and edited goals to persist")


class GoalSaveResponse(BaseModel):
    status: str = "success"
    message: str
    saved_goals_count: int
    saved_tasks_count: int
    goal_ids: List[str] = Field(default_factory=list)
    task_ids: List[str] = Field(default_factory=list)
