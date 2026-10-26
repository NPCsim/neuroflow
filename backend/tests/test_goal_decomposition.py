import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status

from app.models import Goal, Task
from app.schemas.goal_decomposition import (
    GoalDecompositionLLMResponse,
    GoalDecomposition,
    TaskDecomposition,
)
from app.services.goal_decomposition import (
    AbsurdOutputError,
    decompose_goals_with_gemini,
    validate_decomposition,
)


def test_decompose_goals_happy_path_mocked_llm(client, monkeypatch):
    """
    POST /goals/decompose with clear input like:
    'Prepare for my DBMS exam in 10 days and finish my hackathon project'
    returns one or more goals, each with tasks containing title, est_minutes,
    importance 1-5, deadline, depends_on by index, category, and a one-line rationale.
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    mock_llm_response = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                id=str(uuid.uuid4()),
                title="Prepare for DBMS Exam",
                description="Study indexing, transactions, and SQL normalization for final exam",
                target_date=(fixed_now + timedelta(days=10)).isoformat(),
                tasks=[
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Review ER Diagrams and Relational Algebra",
                        est_minutes=120,
                        importance=5,
                        deadline=(fixed_now + timedelta(days=3)).isoformat(),
                        depends_on=[],
                        category="study",
                        rationale="Core conceptual foundation required for all exam questions.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Practice B+ Trees and Query Optimization",
                        est_minutes=90,
                        importance=4,
                        deadline=(fixed_now + timedelta(days=6)).isoformat(),
                        depends_on=[0],
                        category="study",
                        rationale="Complex problem set with high points weighting on exam.",
                    ),
                ],
            ),
            GoalDecomposition(
                id=str(uuid.uuid4()),
                title="Finish Hackathon Project",
                description="Finalize AI scheduler MVP and demo video",
                target_date=(fixed_now + timedelta(days=5)).isoformat(),
                tasks=[
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Implement Diff Preview Modal",
                        est_minutes=180,
                        importance=5,
                        deadline=(fixed_now + timedelta(days=2)).isoformat(),
                        depends_on=[],
                        category="engineering",
                        rationale="Critical UI component demonstrating autonomous scheduling diffs.",
                    ),
                    TaskDecomposition(
                        id=str(uuid.uuid4()),
                        title="Record 3-Minute Demo Video",
                        est_minutes=60,
                        importance=4,
                        deadline=(fixed_now + timedelta(days=4)).isoformat(),
                        depends_on=[0],
                        category="presentation",
                        rationale="Key deliverable evaluated by hackathon judges.",
                    ),
                ],
            ),
        ],
    )

    with patch("app.routers.goals.decompose_goals_with_gemini", return_value=mock_llm_response):
        response = client.post(
            "/goals/decompose",
            json={
                "prompt": "Prepare for my DBMS exam in 10 days and finish my hackathon project",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["needs_clarification"] is False
    assert len(data["clarifying_questions"]) == 0
    assert data["can_save"] is True
    assert len(data["goals"]) == 2

    # Verify first goal
    g1 = data["goals"][0]
    assert g1["title"] == "Prepare for DBMS Exam"
    assert len(g1["tasks"]) == 2
    t0 = g1["tasks"][0]
    assert t0["title"] == "Review ER Diagrams and Relational Algebra"
    assert t0["est_minutes"] == 120
    assert 1 <= t0["importance"] <= 5
    assert t0["depends_on"] == []
    assert t0["category"] == "study"
    assert len(t0["rationale"]) > 5

    t1 = g1["tasks"][1]
    assert t1["depends_on"] == [0]

    # Verify second goal
    g2 = data["goals"][1]
    assert g2["title"] == "Finish Hackathon Project"
    assert len(g2["tasks"]) == 2


def test_decompose_goals_asks_clarifying_questions_when_deadline_missing(client):
    """
    When the deadline or scope is missing from the goal statement (e.g. 'Prepare for my DBMS exam'),
    the endpoint asks clarifying questions in the response instead of guessing.
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    mock_llm_response = GoalDecompositionLLMResponse(
        needs_clarification=True,
        clarifying_questions=[
            "When is your DBMS exam scheduled (what is your target deadline)?",
            "Which syllabus chapters or specific topics do you need to cover?",
        ],
        goals=[],
    )

    with patch("app.routers.goals.decompose_goals_with_gemini", return_value=mock_llm_response):
        response = client.post(
            "/goals/decompose",
            json={
                "prompt": "Prepare for my DBMS exam",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["needs_clarification"] is True
    assert len(data["clarifying_questions"]) >= 1
    assert data["can_save"] is False
    assert any("deadline" in q.lower() or "when" in q.lower() for q in data["clarifying_questions"])


def test_decompose_goals_empty_prompt_asks_clarification(client):
    """
    An empty or whitespace prompt immediately returns clarifying questions.
    """
    response = client.post("/goals/decompose", json={"prompt": "   "})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["needs_clarification"] is True
    assert len(data["clarifying_questions"]) > 0


def test_decompose_goals_rejects_tasks_over_8_hours(client):
    """
    Validation rejects absurd outputs where any task duration exceeds 8 hours (480 minutes).
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    # 600 minutes = 10 hours > 8 hours
    mock_absurd_duration = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                title="Massive Project",
                tasks=[
                    TaskDecomposition(
                        title="Write entire backend in one sitting",
                        est_minutes=600,
                        importance=5,
                        category="engineering",
                        rationale="Absurd monolithic task that should be split.",
                    ),
                ],
            ),
        ],
    )

    with patch("app.services.goal_decomposition._call_gemini_api_with_retry") as mock_api:
        mock_response = MagicMock()
        mock_response.parsed = mock_absurd_duration
        mock_response.text = None
        mock_api.return_value = mock_response

        response = client.post(
            "/goals/decompose",
            json={
                "prompt": "Build entire backend in 2 days",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "8 hours" in response.json()["detail"] or "480" in response.json()["detail"]


def test_decompose_goals_rejects_circular_dependencies(client):
    """
    Validation rejects absurd outputs with circular dependencies among tasks.
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    # Task 0 depends on Task 1, and Task 1 depends on Task 0 -> Cycle!
    mock_circular = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                title="Circular Goal",
                tasks=[
                    TaskDecomposition(
                        title="Task Alpha",
                        est_minutes=60,
                        importance=4,
                        depends_on=[1],
                        category="engineering",
                        rationale="Depends on Beta.",
                    ),
                    TaskDecomposition(
                        title="Task Beta",
                        est_minutes=60,
                        importance=4,
                        depends_on=[0],
                        category="engineering",
                        rationale="Depends on Alpha.",
                    ),
                ],
            ),
        ],
    )

    with patch("app.services.goal_decomposition._call_gemini_api_with_retry") as mock_api:
        mock_response = MagicMock()
        mock_response.parsed = mock_circular
        mock_response.text = None
        mock_api.return_value = mock_response

        response = client.post(
            "/goals/decompose",
            json={
                "prompt": "Complete circular tasks in 5 days",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "circular dependency" in response.json()["detail"].lower()


def test_decompose_goals_rejects_self_dependency(client):
    """
    Validation rejects a task depending on itself.
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    mock_self_dep = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                title="Self Dependent Goal",
                tasks=[
                    TaskDecomposition(
                        title="Self Looping Task",
                        est_minutes=60,
                        importance=3,
                        depends_on=[0],  # Depends on itself
                        category="ops",
                        rationale="Invalid self dependency.",
                    ),
                ],
            ),
        ],
    )

    with patch("app.services.goal_decomposition._call_gemini_api_with_retry") as mock_api:
        mock_response = MagicMock()
        mock_response.parsed = mock_self_dep
        mock_response.text = None
        mock_api.return_value = mock_response

        response = client.post(
            "/goals/decompose",
            json={
                "prompt": "Do loop in 3 days",
                "reference_time": fixed_now.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "cannot depend on itself" in response.json()["detail"].lower()


def test_user_can_review_edit_and_save_decomposed_goals(client, db_session):
    """
    Verifies that the user can review and edit decomposed goals/tasks before
    explicitly saving them to the database via POST /goals/save.
    """
    fixed_now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Step 1: User requests decomposition
    mock_decomposed = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                title="Launch NeuroFlow MVP",
                description="Core hackathon release",
                target_date=(fixed_now + timedelta(days=7)).isoformat(),
                tasks=[
                    TaskDecomposition(
                        title="Draft Feature Spec",
                        est_minutes=90,
                        importance=4,
                        depends_on=[],
                        category="product",
                        rationale="Initial requirements document.",
                    ),
                    TaskDecomposition(
                        title="Implement Core API",
                        est_minutes=180,
                        importance=5,
                        depends_on=[0],
                        category="engineering",
                        rationale="Server endpoints for frontend consumption.",
                    ),
                ],
            ),
        ],
    )

    with patch("app.routers.goals.decompose_goals_with_gemini", return_value=mock_decomposed):
        decomp_res = client.post(
            "/goals/decompose",
            json={"prompt": "Launch NeuroFlow MVP in 7 days"},
        )
    assert decomp_res.status_code == status.HTTP_200_OK
    staged_data = decomp_res.json()

    # Verify nothing was saved to database yet (review mode)
    assert db_session.query(Goal).filter_by(title="Launch NeuroFlow MVP").first() is None

    # 2. Step 2: User reviews and edits the payload
    # E.g. user modifies a title, reduces est_minutes from 180 to 120, and adds an extra task
    edited_goals = staged_data["goals"]
    edited_goals[0]["title"] = "Launch NeuroFlow MVP (Reviewed)"
    edited_goals[0]["tasks"][1]["title"] = "Implement Core FastAPI Endpoints"
    edited_goals[0]["tasks"][1]["est_minutes"] = 120

    edited_goals[0]["tasks"].append(
        {
            "title": "Perform Smoke Testing",
            "est_minutes": 45,
            "importance": 4,
            "depends_on": [1],
            "category": "testing",
            "rationale": "Verify endpoint stability before release.",
        }
    )

    # 3. Step 3: User saves edited goals
    save_res = client.post("/goals/save", json={"goals": edited_goals})
    assert save_res.status_code == status.HTTP_200_OK

    save_data = save_res.json()
    assert save_data["status"] == "success"
    assert save_data["saved_goals_count"] == 1
    assert save_data["saved_tasks_count"] == 3

    # 4. Verify persisted in database
    db_goal = db_session.query(Goal).filter_by(title="Launch NeuroFlow MVP (Reviewed)").first()
    assert db_goal is not None
    assert len(db_goal.tasks) == 3

    task_titles = [t.title for t in db_goal.tasks]
    assert "Draft Feature Spec" in task_titles
    assert "Implement Core FastAPI Endpoints" in task_titles
    assert "Perform Smoke Testing" in task_titles

    # Verify edited duration
    t_api = [t for t in db_goal.tasks if t.title == "Implement Core FastAPI Endpoints"][0]
    assert t_api.estimated_duration_minutes == 120


def test_user_save_validates_and_rejects_invalid_edits(client):
    """
    If the user's manual edits introduce an absurd duration (> 8h) or circular dependencies,
    POST /goals/save rejects it with HTTP 422.
    """
    invalid_payload = {
        "goals": [
            {
                "title": "Bad Goal",
                "tasks": [
                    {
                        "title": "Oversized Task",
                        "est_minutes": 500,  # > 480 mins
                        "importance": 3,
                        "depends_on": [],
                        "category": "engineering",
                        "rationale": "Too long.",
                    }
                ],
            }
        ]
    }
    response = client.post("/goals/save", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "8 hours" in response.json()["detail"] or "480" in response.json()["detail"]


def test_llm_retries_and_backoff_on_transient_failure():
    """
    Tests that decompose_goals_with_gemini retries on transient connection errors
    with exponential backoff and succeeds on subsequent attempts.
    """
    mock_client = MagicMock()

    # Fail twice with ConnectionError, then succeed
    mock_success = MagicMock()
    mock_success.parsed = GoalDecompositionLLMResponse(
        needs_clarification=False,
        clarifying_questions=[],
        goals=[
            GoalDecomposition(
                title="Resilient Goal",
                tasks=[
                    TaskDecomposition(
                        title="Task 1",
                        est_minutes=60,
                        importance=3,
                        depends_on=[],
                        category="ops",
                        rationale="Test retry resilience.",
                    )
                ],
            )
        ],
    )
    mock_success.text = None

    mock_client.models.generate_content.side_effect = [
        ConnectionError("Temporary network timeout"),
        TimeoutError("Request timed out"),
        mock_success,
    ]

    result = decompose_goals_with_gemini(
        prompt="Setup monitoring in 7 days",
        client=mock_client,
    )

    assert result.needs_clarification is False
    assert len(result.goals) == 1
    assert result.goals[0].title == "Resilient Goal"
    assert mock_client.models.generate_content.call_count == 3
