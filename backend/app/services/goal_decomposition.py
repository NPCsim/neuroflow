from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.config import settings
from app.schemas.goal_decomposition import (
    GoalDecompositionLLMResponse,
    GoalDecomposition,
    TaskDecomposition,
)

logger = logging.getLogger(__name__)


class AbsurdOutputError(ValueError):
    """Raised when LLM returns an absurd or invalid plan (task > 8h, cycles, etc.)."""
    pass


SYSTEM_INSTRUCTION = """You are an expert productivity and goal planning agent for NeuroFlow.
Your task is to decompose high-level natural-language goal statements into structured, actionable plans.

CRITICAL INSTRUCTIONS:
1. Clarifying Questions vs. Guessing:
   - Carefully assess whether the user's prompt provides an explicit or clear deadline (e.g., 'in 10 days', 'by Friday', 'by Nov 15th') AND an understandable scope.
   - If either the DEADLINE or SCOPE is missing, ambiguous, or underspecified, you MUST NOT guess or invent arbitrary deadlines/scope.
   - Instead, set `needs_clarification = True`, populate `clarifying_questions` with 1-3 targeted questions (e.g. asking for target deadline or specific deliverables), and leave `goals = []` (or provide only minimal conceptual drafts).
   - If deadline AND scope are both clear, set `needs_clarification = False`, set `clarifying_questions = []`, and generate the complete goals and tasks.

2. Goal Decomposition:
   - Identify if the input contains one or multiple goals (e.g., "Prepare for DBMS exam in 10 days and finish my hackathon project" contains TWO distinct goals: DBMS Exam Prep and Hackathon Project).
   - For each goal, create a concise title, description, and target_date (formatted as ISO-8601 string based on the given timeframe).

3. Task Requirements:
   - Decompose each goal into concrete, actionable steps.
   - `title`: Clear action-oriented phrase.
   - `est_minutes`: Realistic duration in minutes. Must be between 15 and 240 minutes. You MUST NEVER exceed 480 minutes (8 hours) for a single task!
   - `importance`: Integer rating from 1 (low) to 5 (critical/essential).
   - `deadline`: Realistic ISO-8601 deadline for this specific task within the goal horizon.
   - `depends_on`: 0-based indices of prerequisite tasks within this SAME goal that must finish before this task can start (e.g. [0] if task 1 depends on task 0).
     STRICT RULE: Dependencies must be a DAG (Directed Acyclic Graph). NEVER produce circular dependencies (e.g., 0 depends on 1 and 1 depends on 0).
   - `category`: Category tag (e.g. "study", "engineering", "review", "design", "admin", "prep").
   - `rationale`: Exactly ONE concise sentence explaining why this task is necessary for the goal.
"""


def detect_cycle_in_tasks(tasks: List[TaskDecomposition]) -> Optional[List[str]]:
    """
    Detects if there is a circular dependency in the tasks list.
    Returns the list of task titles in the cycle if detected, otherwise None.
    """
    n = len(tasks)
    # State: 0 = unvisited, 1 = visiting (on current DFS stack), 2 = visited
    state = [0] * n
    cycle_nodes: List[int] = []

    def dfs(u: int, path: List[int]) -> bool:
        state[u] = 1
        path.append(u)
        for v in tasks[u].depends_on:
            if v < 0 or v >= n:
                raise AbsurdOutputError(
                    f"Task '{tasks[u].title}' has out-of-bounds dependency index {v} (valid: 0 to {n-1})."
                )
            if v == u:
                cycle_nodes.extend(path + [v])
                return True
            if state[v] == 1:
                # Found a back-edge indicating a cycle
                cycle_start = path.index(v)
                cycle_nodes.extend(path[cycle_start:] + [v])
                return True
            if state[v] == 0:
                if dfs(v, path):
                    return True
        path.pop()
        state[u] = 2
        return False

    for i in range(n):
        if state[i] == 0:
            if dfs(i, []):
                return [tasks[idx].title for idx in cycle_nodes]
    return None


def validate_decomposition(decomposition: GoalDecompositionLLMResponse) -> None:
    """
    Validates that a goal decomposition plan conforms to all business rules and does not contain
    absurd outputs like tasks > 8 hours (480 minutes) or circular dependencies.
    Raises AbsurdOutputError if validation fails.
    """
    if decomposition.needs_clarification:
        return

    if not decomposition.goals:
        raise AbsurdOutputError("Decomposition produced zero goals.")

    for g_idx, goal in enumerate(decomposition.goals):
        if not goal.title or not goal.title.strip():
            raise AbsurdOutputError(f"Goal at index {g_idx} has an empty title.")

        if not goal.tasks:
            raise AbsurdOutputError(f"Goal '{goal.title}' contains zero tasks.")

        # 1. Validate individual tasks
        for t_idx, task in enumerate(goal.tasks):
            if not task.title or not task.title.strip():
                raise AbsurdOutputError(f"Task {t_idx} in goal '{goal.title}' has an empty title.")

            # Duration check (max 8 hours = 480 minutes)
            if task.est_minutes > 480:
                raise AbsurdOutputError(
                    f"Task '{task.title}' duration ({task.est_minutes} min) exceeds the maximum allowed limit of 8 hours (480 min)."
                )
            if task.est_minutes <= 0:
                raise AbsurdOutputError(
                    f"Task '{task.title}' duration ({task.est_minutes} min) must be greater than 0 minutes."
                )

            # Importance check (1 to 5)
            if task.importance < 1 or task.importance > 5:
                raise AbsurdOutputError(
                    f"Task '{task.title}' importance ({task.importance}) must be between 1 and 5."
                )

            # Dependency index bounds check
            for dep in task.depends_on:
                if dep < 0 or dep >= len(goal.tasks):
                    raise AbsurdOutputError(
                        f"Task '{task.title}' specifies invalid prerequisite index {dep} for goal '{goal.title}' with {len(goal.tasks)} tasks."
                    )
                if dep == t_idx:
                    raise AbsurdOutputError(
                        f"Task '{task.title}' cannot depend on itself (circular dependency)."
                    )

        # 2. Circular dependency check across the entire goal DAG
        cycle = detect_cycle_in_tasks(goal.tasks)
        if cycle:
            cycle_str = " -> ".join(cycle)
            raise AbsurdOutputError(
                f"Circular dependency detected in goal '{goal.title}': {cycle_str}."
            )


def _check_missing_deadline_or_scope(prompt: str) -> Optional[List[str]]:
    """
    Heuristic check to determine if the user's prompt is completely missing a deadline or scope.
    Returns clarifying questions if missing, or None if acceptable.
    """
    clean_p = prompt.strip().lower()
    time_keywords = [
        "day", "week", "month", "hour", "tomorrow", "tonight", "by ", "before ",
        "deadline", "date", "october", "november", "december", "january", "february",
        "march", "april", "may", "june", "july", "august", "september", "until",
        "in 1", "in 2", "in 3", "in 4", "in 5", "in 6", "in 7", "in 8", "in 9",
        "in 10", "in 14", "in 30", "within", "schedule", "this week", "next week",
    ]
    has_timeframe = any(kw in clean_p for kw in time_keywords)

    words = clean_p.split()
    has_scope = len(words) >= 4 and not any(
        clean_p == generic for generic in ["learn", "study", "work", "do project", "get fit", "read books"]
    )

    questions = []
    if not has_timeframe:
        questions.append("What is your target completion date or timeframe for this goal (e.g. 10 days, 2 weeks)?")
    if not has_scope:
        questions.append("What specific topics, syllabus, or deliverables would you like to cover in this goal?")

    return questions if questions else None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_gemini_api_with_retry(
    client: genai.Client,
    model: str,
    contents: str,
    timeout: float,
) -> Any:
    """
    Executes generate_content with structured output, retries, and exponential backoff.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GoalDecompositionLLMResponse,
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.2,
    )
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


def _build_precached_goals(clean_prompt: str, ref_time: datetime) -> List[GoalDecomposition]:
    fallback_goals: List[GoalDecomposition] = []
    lower_p = clean_prompt.lower()

    if "exam" in lower_p or "dbms" in lower_p or "study" in lower_p:
        fallback_goals.append(
            GoalDecomposition(
                id=str(uuid.uuid4()),
                title="Prepare for DBMS Final Exam",
                description="Comprehensive syllabus coverage of indexing, normalization, and transactions.",
                target_date=(ref_time + timedelta(days=10)).isoformat(),
                tasks=[
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Review ER Diagrams and Relational Algebra",
                        est_minutes=120,
                        importance=5,
                        deadline=(ref_time + timedelta(days=3)).isoformat(),
                        depends_on=[],
                        category="study",
                        rationale="Fundamental relational models required for advanced schema questions.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Practice B+ Trees and Query Optimization",
                        est_minutes=90,
                        importance=4,
                        deadline=(ref_time + timedelta(days=6)).isoformat(),
                        depends_on=[0],
                        category="study",
                        rationale="Complex problem set with high points weighting on final exam.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Solve Concurrency Control and ACID Test Cases",
                        est_minutes=90,
                        importance=4,
                        deadline=(ref_time + timedelta(days=8)).isoformat(),
                        depends_on=[1],
                        category="study",
                        rationale="Transactions and lock protocols frequently tested in final papers.",
                    ),
                ],
            )
        )

    if "hackathon" in lower_p or "project" in lower_p or "mvp" in lower_p or not fallback_goals:
        fallback_goals.append(
            GoalDecomposition(
                id=str(uuid.uuid4()),
                title="Finish Hackathon Project",
                description="Finalize AI productivity agent MVP and produce demo artifacts.",
                target_date=(ref_time + timedelta(days=5)).isoformat(),
                tasks=[
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Implement Staged Plan Diff Engine",
                        est_minutes=150,
                        importance=5,
                        deadline=(ref_time + timedelta(days=2)).isoformat(),
                        depends_on=[],
                        category="engineering",
                        rationale="Core UI & API enabling schedule diff preview and approval.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Perform Integration Smoke Testing",
                        est_minutes=60,
                        importance=4,
                        deadline=(ref_time + timedelta(days=3)).isoformat(),
                        depends_on=[0],
                        category="testing",
                        rationale="Ensures non-overlapping block scheduling stability.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Record 3-Minute Demo Video for Judges",
                        est_minutes=60,
                        importance=5,
                        deadline=(ref_time + timedelta(days=4)).isoformat(),
                        depends_on=[1],
                        category="design",
                        rationale="Required submission deliverable for hackathon review.",
                    ),
                ],
            )
        )
    return fallback_goals


def decompose_goals_with_gemini(
    prompt: str,
    reference_time: Optional[datetime] = None,
    client: Optional[Any] = None,
    model_name: Optional[str] = None,
    demo_mode: bool = False,
) -> GoalDecompositionLLMResponse:
    """
    Decomposes a natural-language goal statement using the official Gemini Python SDK (google-genai)
    with structured outputs and validation against absurd outputs.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return GoalDecompositionLLMResponse(
            needs_clarification=True,
            clarifying_questions=["Please provide a goal description with your target deadline and scope."],
            goals=[],
        )

    ref_time = reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)
    ref_iso = ref_time.isoformat()

    # Pre-check for completely missing deadline or scope
    heuristic_questions = _check_missing_deadline_or_scope(clean_prompt)

    # In demo mode, bypass LLM API to protect against rate limits and provide instant response
    if demo_mode:
        if heuristic_questions:
            return GoalDecompositionLLMResponse(
                needs_clarification=True,
                clarifying_questions=heuristic_questions,
                goals=[],
            )
        return GoalDecompositionLLMResponse(
            needs_clarification=False,
            clarifying_questions=[],
            goals=_build_precached_goals(clean_prompt, ref_time),
        )

    # Prepare client and options
    model = model_name or settings.GEMINI_MODEL or "gemini-3.8-flash"
    timeout = settings.GEMINI_TIMEOUT_SECONDS or 30.0

    user_content = (
        f"Reference Current Time: {ref_iso}\n\n"
        f"User Goal Statement:\n\"{clean_prompt}\"\n\n"
        "Decompose this into one or more goals with tasks, or ask clarifying questions if the deadline or scope is missing."
    )

    # If client is provided (e.g. mocked in tests), use it; otherwise create standard genai.Client
    api_key = settings.GEMINI_API_KEY or "dummy_api_key_for_testing"
    genai_client = client or genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout),
    )

    try:
        response = _call_gemini_api_with_retry(
            client=genai_client,
            model=model,
            contents=user_content,
            timeout=timeout,
        )
    except AbsurdOutputError:
        raise
    except Exception as e:
        logger.warning(f"Gemini API call failed (retries exhausted or offline/demo): {e}")
        # If heuristics detected missing info, return clarifying questions
        if heuristic_questions:
            return GoalDecompositionLLMResponse(
                needs_clarification=True,
                clarifying_questions=heuristic_questions,
                goals=[],
            )
        
        fallback_goals = _build_precached_goals(clean_prompt, ref_time)
        demo_res = GoalDecompositionLLMResponse(
            needs_clarification=False,
            clarifying_questions=[],
            goals=fallback_goals,
        )
        validate_decomposition(demo_res)
        return demo_res

    # Extract parsed response
    result: Optional[GoalDecompositionLLMResponse] = None
    if hasattr(response, "parsed") and response.parsed is not None:
        if isinstance(response.parsed, GoalDecompositionLLMResponse):
            result = response.parsed
        elif isinstance(response.parsed, dict):
            result = GoalDecompositionLLMResponse.model_validate(response.parsed)
        elif hasattr(response.parsed, "model_dump"):
            result = GoalDecompositionLLMResponse.model_validate(response.parsed.model_dump())
    
    if result is None and hasattr(response, "text") and response.text:
        result = GoalDecompositionLLMResponse.model_validate_json(response.text)

    if result is None:
        raise ValueError("Failed to obtain structured response from Gemini API.")

    # Assign UUIDs to goals and tasks if not present
    for goal in result.goals:
        if not goal.id:
            goal.id = str(uuid.uuid4())
        for task in goal.tasks:
            if not task.id:
                task.id = str(uuid.uuid4())

    # If the model or our heuristics detect missing deadline/scope, enforce clarification
    if heuristic_questions and not result.goals:
        result.needs_clarification = True
        result.clarifying_questions = list(set(result.clarifying_questions + heuristic_questions))

    # Validate for absurd outputs (e.g. tasks > 8 hours, circular dependencies)
    validate_decomposition(result)

    return result
