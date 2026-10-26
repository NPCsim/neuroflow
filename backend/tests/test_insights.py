from __future__ import annotations

import json
import uuid
from datetime import datetime, date, time, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status

from app.models import ActivityLog, Task, ScheduleBlock, UserSettings
from app.schemas.insights import RecommendationItem, RecommendationListLLMResponse
from app.services.insights_service import (
    clear_insights_cache,
    compute_activity_log_stats,
    generate_recommendations_from_stats,
)


@pytest.fixture(autouse=True)
def reset_cache_before_each_test():
    clear_insights_cache()
    yield
    clear_insights_cache()


@pytest.fixture
def populated_activity_logs(db_session):
    """
    Populates diverse ActivityLog records:
      - Coding tasks: 9/10 completed before noon (90%), 5/10 completed afternoon (50%) -> 40% morning advantage!
      - Study tasks: 4 completed, 1 missed (80% completion rate).
      - Admin tasks: 2 completed, 4 missed (33.3% completion rate -> top missed).
      - Planned vs actual durations: planned 60, actual 75 -> ratio 1.25x.
      - Overload day: 2026-10-22 has 3 missed blocks.
    """
    base_date = datetime(2026, 10, 26, 9, 0, 0, tzinfo=timezone.utc)
    overload_date = datetime(2026, 10, 22, 18, 0, 0, tzinfo=timezone.utc)

    # Coding task
    t_code = Task(
        id=str(uuid.uuid4()),
        title="Backend API Development",
        description="Core engineering coding task",
        estimated_duration_minutes=60,
    )
    # Admin task
    t_admin = Task(
        id=str(uuid.uuid4()),
        title="Weekly Status Reports and Admin",
        description="Administrative sync",
        estimated_duration_minutes=60,
    )
    # Study task
    t_study = Task(
        id=str(uuid.uuid4()),
        title="DBMS Exam Reading",
        description="Academic study preparation",
        estimated_duration_minutes=60,
    )
    db_session.add_all([t_code, t_admin, t_study])
    db_session.commit()

    logs: list[ActivityLog] = []

    # 1. Coding before noon: 9 completed, 1 missed (morning rate: 90%)
    for i in range(10):
        action = "completed" if i < 9 else "missed"
        morning_dt = base_date.replace(hour=10, minute=i * 5)
        logs.append(
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=t_code.id,
                action=action,
                title="Code API Endpoint",
                details={
                    "category": "coding",
                    "start_time": morning_dt.isoformat(),
                    "planned_minutes": 60,
                    "actual_minutes": 75 if action == "completed" else 90,
                },
                created_at=morning_dt,
            )
        )

    # 2. Coding afternoon: 5 completed, 5 missed (afternoon rate: 50%)
    for i in range(10):
        action = "completed" if i < 5 else "missed"
        afternoon_dt = base_date.replace(hour=14, minute=i * 5)
        logs.append(
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=t_code.id,
                action=action,
                title="Code Frontend Feature",
                details={
                    "category": "coding",
                    "start_time": afternoon_dt.isoformat(),
                    "planned_minutes": 60,
                    "actual_minutes": 75 if action == "completed" else 90,
                },
                created_at=afternoon_dt,
            )
        )

    # 3. Admin: 2 completed, 4 missed (missed rate: 66.7%)
    for i in range(6):
        action = "completed" if i < 2 else "missed"
        dt = base_date.replace(hour=13, minute=i * 8)
        logs.append(
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=t_admin.id,
                action=action,
                title="Status Update & Emails",
                details={
                    "category": "admin",
                    "start_time": dt.isoformat(),
                    "planned_minutes": 30,
                    "actual_minutes": 30,
                },
                created_at=dt,
            )
        )

    # 4. Study: 4 completed, 1 missed (rate: 80%)
    for i in range(5):
        action = "completed" if i < 4 else "missed"
        dt = base_date.replace(hour=11, minute=i * 10)
        logs.append(
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=t_study.id,
                action=action,
                title="Read DBMS Chapters",
                details={
                    "category": "study",
                    "start_time": dt.isoformat(),
                    "planned_minutes": 60,
                    "actual_minutes": 60,
                },
                created_at=dt,
            )
        )

    # 5. Overload day (2026-10-22): 3 missed blocks
    for i in range(3):
        logs.append(
            ActivityLog(
                id=str(uuid.uuid4()),
                task_id=t_code.id,
                action="missed",
                title=f"Overloaded block {i}",
                details={
                    "category": "coding",
                    "start_time": overload_date.isoformat(),
                    "planned_minutes": 60,
                    "actual_minutes": 90,
                },
                created_at=overload_date,
            )
        )

    db_session.add_all(logs)
    db_session.commit()

    return {
        "base_date": base_date,
        "logs_count": len(logs),
        "t_code": t_code,
        "t_admin": t_admin,
    }


def test_plain_python_stats_computation(db_session, populated_activity_logs):
    """
    Verifies that compute_activity_log_stats calculates exact stats in plain Python:
      - Completion rate by category.
      - Completion rate by time of day (and category x time of day diff).
      - Planned vs actual duration ratio (e.g. 75/60 = 1.25).
      - Most-missed task types (admin highest).
      - Overload days (2026-10-22 detected).
    """
    logs = db_session.query(ActivityLog).all()
    tasks = db_session.query(Task).all()

    stats = compute_activity_log_stats(logs=logs, tasks=tasks)

    # 1. Category stats
    cat_stats = stats["completion_rate_by_category"]
    assert "coding" in cat_stats
    assert "admin" in cat_stats
    assert "study" in cat_stats

    # Coding has 9 morning completed + 5 afternoon completed = 14 completed out of (10+10+3=23)
    assert cat_stats["coding"]["completed"] == 14
    assert cat_stats["coding"]["missed"] == 9

    # Admin has 2 completed, 4 missed
    assert cat_stats["admin"]["completed"] == 2
    assert cat_stats["admin"]["missed"] == 4
    assert cat_stats["admin"]["completion_rate_pct"] == 33.3

    # 2. Category x Time of Day (the prompt's example: coding 40% higher before noon)
    cat_tod = stats["category_by_time_of_day"]
    coding_tod = cat_tod["coding"]
    assert coding_tod["morning_rate_pct"] == 90.0
    assert coding_tod["afternoon_rate_pct"] == 50.0
    assert coding_tod["morning_vs_afternoon_diff_pct"] == 40.0

    # 3. Planned vs actual duration ratio
    dur = stats["planned_vs_actual_duration"]
    assert dur["overall_ratio"] >= 1.15
    assert dur["trend"] == "overrun"

    # 4. Most missed task types
    most_missed = stats["most_missed_task_types"]
    assert len(most_missed) >= 1
    # Check that admin has a high missed rate (0.67)
    admin_entry = [m for m in most_missed if m["category"] == "admin"][0]
    assert admin_entry["missed_count"] == 4

    # 5. Overload days
    overload_days = stats["overload_days"]
    assert len(overload_days) >= 1
    dates = [o["date"] for o in overload_days]
    assert "2026-10-22" in dates


def test_send_only_stats_to_gemini_and_strict_grounding(populated_activity_logs):
    """
    Verifies that:
      - ONLY the computed stats JSON is sent to Gemini (no extra raw messages).
      - The prompt forbids claims not supported by the supplied stats.
    """
    sample_stats = {
        "overall_completion_rate_pct": 65.0,
        "completion_rate_by_category": {
            "coding": {"completion_rate_pct": 70.0, "completed": 14, "missed": 6},
            "admin": {"completion_rate_pct": 33.3, "completed": 2, "missed": 4},
        },
        "category_by_time_of_day": {
            "coding": {
                "morning_rate_pct": 90.0,
                "afternoon_rate_pct": 50.0,
                "morning_vs_afternoon_diff_pct": 40.0,
            }
        },
        "planned_vs_actual_duration": {"overall_ratio": 1.25, "trend": "overrun"},
        "most_missed_task_types": [{"category": "admin", "missed_count": 4, "missed_rate_pct": 66.7}],
        "overload_days": [{"date": "2026-10-22", "missed_blocks_count": 3, "status": "overloaded"}],
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = RecommendationListLLMResponse(
        recommendations=[
            RecommendationItem(
                id="rec-1",
                title="Schedule Coding Before Noon",
                description="You finish coding tasks 40% more often before noon; I moved 2 coding blocks earlier.",
                category="coding",
                impact="high",
                supporting_metric="Coding morning rate 90% vs afternoon 50% (+40%)",
            ),
            RecommendationItem(
                id="rec-2",
                title="Add 15m Buffer for Estimation Overrun",
                description="Your tasks take 1.25x longer than planned; increase buffer between focus blocks.",
                category="estimation",
                impact="high",
                supporting_metric="Actual vs planned duration ratio is 1.25x",
            ),
            RecommendationItem(
                id="rec-3",
                title="Chunk Admin Tasks",
                description="Admin tasks represent your highest failure rate at 66.7%; split them into 15m chunks.",
                category="admin",
                impact="medium",
                supporting_metric="Admin missed rate is 66.7% with 4 missed blocks",
            ),
        ]
    )
    mock_client.models.generate_content.return_value = mock_response

    recs = generate_recommendations_from_stats(stats=sample_stats, client=mock_client)

    assert len(recs) == 3
    assert recs[0].title == "Schedule Coding Before Noon"
    assert "40%" in recs[0].description

    # Inspect the prompt passed to Gemini
    called_contents = mock_client.models.generate_content.call_args[1]["contents"]
    prompt_text = called_contents[0]

    # Verify prompt contains computed stats
    assert "COMPUTED PRODUCTIVITY STATS" in prompt_text
    assert '"overall_completion_rate_pct": 65.0' in prompt_text
    assert '"morning_vs_afternoon_diff_pct": 40.0' in prompt_text

    # Verify prompt forbids unsupported claims
    assert "STRICT GROUNDING" in prompt_text
    assert "FORBIDDEN" in prompt_text
    assert "not directly supported by the supplied stats" in prompt_text.lower() or "not explicitly present in" in prompt_text.lower()


def test_get_insights_recommendations_endpoint_happy_path(client, db_session, populated_activity_logs):
    """
    Tests GET /insights/recommendations:
      - Returns 200 OK.
      - Returns 3-5 grounded recommendations.
      - Includes computed stats in the payload.
      - Caches the response per day (second call returns is_cached=True).
    """
    mock_llm_response = RecommendationListLLMResponse(
        recommendations=[
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Move Coding Focus Blocks to Morning",
                description="You finish coding tasks 40% more often before noon (90% vs 50%); schedule deep work early.",
                category="coding",
                impact="high",
                supporting_metric="Coding completion rate is 90% before noon vs 50% in the afternoon",
            ),
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Add 15-Minute Buffer Multipliers",
                description="Your tasks take 1.25x longer than planned; expanding transition buffers will prevent daily drift.",
                category="estimation",
                impact="high",
                supporting_metric="Actual to planned ratio is 1.25x",
            ),
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Break Down Weekly Admin Updates",
                description="Admin has the highest missed rate (66.7% failure); decompose administrative tasks into smaller slots.",
                category="admin",
                impact="medium",
                supporting_metric="Admin has 4 missed blocks (66.7% missed rate)",
            ),
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Cap Maximum Daily Focus Load",
                description="Detected overload day on 2026-10-22 with 3 missed blocks; cap scheduled focus at 6.5 hours.",
                category="workload_capacity",
                impact="high",
                supporting_metric="1 overload day detected with 3 missed blocks",
            ),
        ]
    )

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.parsed = mock_llm_response
    mock_client.models.generate_content.return_value = mock_resp

    with patch("app.services.insights_service.genai.Client", return_value=mock_client):
        # 1. First call: fresh generation
        res1 = client.get("/insights/recommendations?date=2026-10-26")
        assert res1.status_code == status.HTTP_200_OK
        data1 = res1.json()

        assert data1["date"] == "2026-10-26"
        assert data1["is_cached"] is False
        assert len(data1["recommendations"]) == 4
        assert "stats" in data1
        assert "completion_rate_by_category" in data1["stats"]
        assert "planned_vs_actual_duration" in data1["stats"]

        rec_titles = [r["title"] for r in data1["recommendations"]]
        assert "Move Coding Focus Blocks to Morning" in rec_titles

        # Verified LLM was called on first request
        assert mock_client.models.generate_content.call_count == 1

        # 2. Second call on same date: served from daily cache!
        res2 = client.get("/insights/recommendations?date=2026-10-26")
        assert res2.status_code == status.HTTP_200_OK
        data2 = res2.json()

        assert data2["date"] == "2026-10-26"
        assert data2["is_cached"] is True
        assert len(data2["recommendations"]) == 4

        # CRITICAL: LLM was NOT called again; served strictly from cache
        assert mock_client.models.generate_content.call_count == 1

        # 3. Third call with force_refresh=true: bypasses cache
        res3 = client.get("/insights/recommendations?date=2026-10-26&force_refresh=true")
        assert res3.status_code == status.HTTP_200_OK
        data3 = res3.json()

        assert data3["is_cached"] is False
        assert mock_client.models.generate_content.call_count == 2
