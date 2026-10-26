from __future__ import annotations

import json
import uuid
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app.config import settings
from app.models import ActivityLog, Task, ScheduleBlock, UserSettings
from app.schemas.insights import (
    RecommendationItem,
    RecommendationListLLMResponse,
    InsightsRecommendationsResponse,
)

# Daily in-memory cache keyed by "YYYY-MM-DD"
_DAILY_RECOMMENDATIONS_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_insights_cache() -> None:
    """Clears the daily recommendations cache (used for tests and cache busting)."""
    global _DAILY_RECOMMENDATIONS_CACHE
    _DAILY_RECOMMENDATIONS_CACHE.clear()


# ---------------------------------------------------------------------------
# Plain Python Stats Computation Helpers
# ---------------------------------------------------------------------------

def _extract_category(log: ActivityLog) -> str:
    """Extracts or infers a task category from log details or task title/description."""
    if log.details and isinstance(log.details, dict):
        cat = log.details.get("category")
        if cat:
            return str(cat).strip().lower()

    title = ""
    desc = ""
    if log.task:
        title = log.task.title or ""
        desc = log.task.description or ""
    elif log.title:
        title = log.title

    text = f"{title} {desc}".lower()
    if any(w in text for w in ["code", "dev", "engineering", "api", "backend", "frontend", "bug", "pr", "deploy", "mvp", "refactor"]):
        return "coding"
    elif any(w in text for w in ["study", "exam", "reading", "learn", "course", "dbms", "research", "prep"]):
        return "study"
    elif any(w in text for w in ["write", "doc", "spec", "report", "draft", "article", "proposal"]):
        return "writing"
    elif any(w in text for w in ["admin", "email", "inbox", "meeting", "sync", "standup", "schedule", "ops"]):
        return "admin"
    elif any(w in text for w in ["design", "ui", "ux", "figma"]):
        return "design"
    return "general"


def _extract_log_datetime(log: ActivityLog) -> datetime:
    """Extracts the start/reference datetime for a log entry."""
    if log.details and isinstance(log.details, dict):
        st = log.details.get("start_time")
        if st:
            try:
                dt = datetime.fromisoformat(str(st).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

    if log.schedule_block and log.schedule_block.start_time:
        st = log.schedule_block.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        return st

    dt = log.created_at or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_time_of_day(log_dt: datetime) -> str:
    """Categorizes datetime into time-of-day: before_noon, afternoon, or evening."""
    h = log_dt.hour
    if h < 12:
        return "before_noon"  # morning
    elif 12 <= h < 17:
        return "afternoon"
    else:
        return "evening"


def compute_activity_log_stats(
    logs: List[ActivityLog],
    tasks: Optional[List[Task]] = None,
    settings_obj: Optional[UserSettings] = None,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Computes all required productivity statistics in plain Python:
      1. Completion rate by category.
      2. Completion rate by time of day (and category by time of day cross-tabulation).
      3. Planned vs actual duration ratio.
      4. Most-missed task types.
      5. Overload days.
    """
    now = reference_time or datetime.now(timezone.utc)

    # 1. Category aggregation
    cat_stats: Dict[str, Dict[str, Any]] = {}
    # 2. Time of day aggregation
    tod_stats: Dict[str, Dict[str, Any]] = {
        "before_noon": {"completed": 0, "missed": 0, "total": 0},
        "afternoon": {"completed": 0, "missed": 0, "total": 0},
        "evening": {"completed": 0, "missed": 0, "total": 0},
    }
    # Cross-tabulation: category x time_of_day
    cat_tod: Dict[str, Dict[str, Dict[str, int]]] = {}

    # 3. Planned vs actual durations
    total_planned_mins = 0
    total_actual_mins = 0
    cat_durations: Dict[str, Dict[str, int]] = {}

    # 4. Missed count by category
    missed_by_cat: Dict[str, int] = {}

    # 5. Daily grouping for overload analysis
    daily_logs: Dict[str, Dict[str, Any]] = {}

    for log in logs:
        action = (log.action or "").strip().lower()
        is_completed = action in ["completed", "done", "finished"]
        is_missed = action in ["missed", "overdue", "incomplete", "cancelled"]

        # Only process completed or missed logs for adherence stats
        if not (is_completed or is_missed):
            continue

        cat = _extract_category(log)
        log_dt = _extract_log_datetime(log)
        tod = _extract_time_of_day(log_dt)
        date_str = log_dt.strftime("%Y-%m-%d")

        # Category stats
        if cat not in cat_stats:
            cat_stats[cat] = {"completed": 0, "missed": 0, "total": 0}
        cat_stats[cat]["total"] += 1
        if is_completed:
            cat_stats[cat]["completed"] += 1
        else:
            cat_stats[cat]["missed"] += 1
            missed_by_cat[cat] = missed_by_cat.get(cat, 0) + 1

        # Time of day stats
        tod_stats[tod]["total"] += 1
        if is_completed:
            tod_stats[tod]["completed"] += 1
        else:
            tod_stats[tod]["missed"] += 1

        # Cross-tabulation
        if cat not in cat_tod:
            cat_tod[cat] = {
                "before_noon": {"completed": 0, "total": 0},
                "afternoon": {"completed": 0, "total": 0},
                "evening": {"completed": 0, "total": 0},
            }
        cat_tod[cat][tod]["total"] += 1
        if is_completed:
            cat_tod[cat][tod]["completed"] += 1

        # Planned vs actual durations
        details = log.details if isinstance(log.details, dict) else {}
        planned_m = details.get("planned_minutes") or details.get("estimated_duration_minutes")
        actual_m = details.get("actual_minutes") or details.get("actual_duration_minutes")

        if not planned_m and log.task:
            planned_m = log.task.estimated_duration_minutes
        if not planned_m and log.schedule_block and log.schedule_block.start_time and log.schedule_block.end_time:
            planned_m = int((log.schedule_block.end_time - log.schedule_block.start_time).total_seconds() / 60)

        # If actual was tracked
        if planned_m and planned_m > 0:
            act = actual_m if (actual_m is not None and actual_m > 0) else (planned_m if is_completed else planned_m + 30)
            total_planned_mins += int(planned_m)
            total_actual_mins += int(act)

            if cat not in cat_durations:
                cat_durations[cat] = {"planned": 0, "actual": 0}
            cat_durations[cat]["planned"] += int(planned_m)
            cat_durations[cat]["actual"] += int(act)

        # Daily overload grouping
        if date_str not in daily_logs:
            daily_logs[date_str] = {"date": date_str, "missed_blocks": 0, "completed_blocks": 0, "total_blocks": 0}
        daily_logs[date_str]["total_blocks"] += 1
        if is_missed:
            daily_logs[date_str]["missed_blocks"] += 1
        else:
            daily_logs[date_str]["completed_blocks"] += 1

    # Format Completion Rate by Category
    formatted_cat_stats: Dict[str, Any] = {}
    for c_name, data in cat_stats.items():
        total = data["total"]
        raw_rate = data["completed"] / total if total > 0 else 0.0
        formatted_cat_stats[c_name] = {
            "completed": data["completed"],
            "missed": data["missed"],
            "total": total,
            "completion_rate": round(raw_rate, 4),
            "completion_rate_pct": round(raw_rate * 100, 1),
        }

    # Format Completion Rate by Time of Day
    formatted_tod_stats: Dict[str, Any] = {}
    for tod_key, data in tod_stats.items():
        total = data["total"]
        raw_rate = data["completed"] / total if total > 0 else 0.0
        formatted_tod_stats[tod_key] = {
            "completed": data["completed"],
            "missed": data["missed"],
            "total": total,
            "completion_rate": round(raw_rate, 4),
            "completion_rate_pct": round(raw_rate * 100, 1),
        }

    # Format Category x Time of Day (e.g. coding before noon vs afternoon)
    formatted_cat_tod: Dict[str, Any] = {}
    for c_name, tods in cat_tod.items():
        morning_total = tods["before_noon"]["total"]
        morning_comp = tods["before_noon"]["completed"]
        morning_rate = morning_comp / morning_total if morning_total > 0 else 0.0

        afternoon_total = tods["afternoon"]["total"]
        afternoon_comp = tods["afternoon"]["completed"]
        afternoon_rate = afternoon_comp / afternoon_total if afternoon_total > 0 else 0.0

        diff_pct = round((morning_rate - afternoon_rate) * 100, 1)

        formatted_cat_tod[c_name] = {
            "morning_rate": round(morning_rate, 4),
            "morning_rate_pct": round(morning_rate * 100, 1),
            "morning_completed": morning_comp,
            "morning_total": morning_total,
            "afternoon_rate": round(afternoon_rate, 4),
            "afternoon_rate_pct": round(afternoon_rate * 100, 1),
            "afternoon_completed": afternoon_comp,
            "afternoon_total": afternoon_total,
            "morning_vs_afternoon_diff_pct": diff_pct,
        }

    # Format Planned vs Actual Ratio
    overall_ratio = round(total_actual_mins / total_planned_mins, 2) if total_planned_mins > 0 else 1.0
    cat_ratios: Dict[str, float] = {}
    for c_name, dur in cat_durations.items():
        cat_ratios[c_name] = round(dur["actual"] / dur["planned"], 2) if dur["planned"] > 0 else 1.0

    duration_ratio_stats = {
        "overall_ratio": overall_ratio,
        "total_planned_minutes": total_planned_mins,
        "total_actual_minutes": total_actual_mins,
        "trend": "overrun" if overall_ratio > 1.05 else ("underrun" if overall_ratio < 0.95 else "on_track"),
        "by_category": cat_ratios,
    }

    # Format Most-Missed Task Types
    most_missed: List[Dict[str, Any]] = []
    for c_name, m_count in sorted(missed_by_cat.items(), key=lambda x: x[1], reverse=True):
        total = cat_stats[c_name]["total"]
        raw_rate = m_count / total if total > 0 else 0.0
        most_missed.append({
            "category": c_name,
            "missed_count": m_count,
            "total_count": total,
            "missed_rate": round(raw_rate, 4),
            "missed_rate_pct": round(raw_rate * 100, 1),
        })

    # Format Overload Days (dates with >= 2 missed blocks or high failure rate)
    overload_days: List[Dict[str, Any]] = []
    for d_str, day_info in sorted(daily_logs.items(), key=lambda x: x[0], reverse=True):
        if day_info["missed_blocks"] >= 2 or (day_info["total_blocks"] >= 3 and day_info["missed_blocks"] / day_info["total_blocks"] >= 0.5):
            overload_days.append({
                "date": d_str,
                "missed_blocks_count": day_info["missed_blocks"],
                "total_blocks_count": day_info["total_blocks"],
                "status": "overloaded",
                "reason": f"{day_info['missed_blocks']} schedule blocks missed on {d_str}",
            })

    total_logs_count = len(logs)
    total_completed = sum(c["completed"] for c in cat_stats.values())
    total_missed = sum(c["missed"] for c in cat_stats.values())
    total_evaluated = total_completed + total_missed
    overall_rate = round(total_completed / total_evaluated, 2) if total_evaluated > 0 else 0.0

    return {
        "total_logs_analyzed": total_logs_count,
        "overall_completion_rate": overall_rate,
        "overall_completion_rate_pct": round(overall_rate * 100, 1),
        "total_completed": total_completed,
        "total_missed": total_missed,
        "completion_rate_by_category": formatted_cat_stats,
        "completion_rate_by_time_of_day": formatted_tod_stats,
        "category_by_time_of_day": formatted_cat_tod,
        "planned_vs_actual_duration": duration_ratio_stats,
        "most_missed_task_types": most_missed,
        "overload_days": overload_days,
    }


# ---------------------------------------------------------------------------
# Deterministic Grounded Recommendations Fallback
# ---------------------------------------------------------------------------

def _generate_fallback_grounded_recommendations(stats: Dict[str, Any]) -> List[RecommendationItem]:
    """
    Generates 3-5 concrete, strictly grounded recommendations derived directly from the computed stats.
    Guarantees every assertion cites the exact numbers from stats.
    """
    recommendations: List[RecommendationItem] = []

    # 1. Recommendation from Category x Time of Day (e.g. coding before noon)
    cat_tod = stats.get("category_by_time_of_day", {})
    if cat_tod:
        for cat, data in cat_tod.items():
            m_pct = data.get("morning_rate_pct", 0)
            a_pct = data.get("afternoon_rate_pct", 0)
            diff = data.get("morning_vs_afternoon_diff_pct", 0)
            if diff >= 20 and data.get("morning_total", 0) >= 1:
                recommendations.append(
                    RecommendationItem(
                        id=str(uuid.uuid4()),
                        title=f"Schedule {cat.title()} Tasks Before Noon",
                        description=(
                            f"You finish {cat} tasks {diff}% more often before noon ({m_pct}% completion rate "
                            f"vs {a_pct}% in the afternoon); reserve morning focus blocks for {cat} work."
                        ),
                        category=cat,
                        impact="high",
                        supporting_metric=f"{cat} morning completion rate is {m_pct}% vs {a_pct}% in the afternoon (+{diff}%)",
                        action_type="reschedule_morning",
                    )
                )
                break

    # If no large category diff, check general time of day
    if not recommendations:
        tod = stats.get("completion_rate_by_time_of_day", {})
        m_pct = tod.get("before_noon", {}).get("completion_rate_pct", 0)
        a_pct = tod.get("afternoon", {}).get("completion_rate_pct", 0)
        if m_pct > a_pct:
            diff = round(m_pct - a_pct, 1)
            recommendations.append(
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    title="Leverage Peak Morning Adherence",
                    description=(
                        f"Your morning task completion rate is {m_pct}%, which is {diff}% higher than afternoon ({a_pct}%). "
                        "Front-load critical high-priority tasks into your 09:00 - 12:00 window."
                    ),
                    category="time_management",
                    impact="high",
                    supporting_metric=f"Morning completion rate {m_pct}% vs afternoon {a_pct}%",
                    action_type="frontload_morning",
                )
            )

    # 2. Recommendation from Planned vs Actual Duration Ratio
    dur = stats.get("planned_vs_actual_duration", {})
    overall_ratio = dur.get("overall_ratio", 1.0)
    if overall_ratio > 1.05:
        overrun_pct = round((overall_ratio - 1.0) * 100, 1)
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Expand Task Buffer Multiplier",
                description=(
                    f"Your tasks take {overall_ratio}x longer than planned ({overrun_pct}% duration overrun on average). "
                    f"Adding a 15-minute buffer between blocks will prevent downstream deadline drift."
                ),
                category="estimation",
                impact="high",
                supporting_metric=f"Actual vs planned duration ratio is {overall_ratio}x ({dur.get('total_actual_minutes')}m actual vs {dur.get('total_planned_minutes')}m planned)",
                action_type="buffer_expansion",
            )
        )
    else:
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Duration Estimates are Well-Calibrated",
                description=(
                    f"Your planned vs actual duration ratio is on track at {overall_ratio}x. "
                    "Maintain current estimation granularity for future task scheduling."
                ),
                category="estimation",
                impact="medium",
                supporting_metric=f"Duration ratio is {overall_ratio}x",
                action_type="maintain_estimates",
            )
        )

    # 3. Recommendation from Most-Missed Task Types
    most_missed = stats.get("most_missed_task_types", [])
    if most_missed:
        top_missed = most_missed[0]
        cat = top_missed["category"]
        m_count = top_missed["missed_count"]
        m_rate = top_missed["missed_rate_pct"]
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                title=f"Split and Defer High-Risk {cat.title()} Tasks",
                description=(
                    f"{cat.title()} tasks represent your highest missed category with {m_count} missed instances "
                    f"({m_rate}% failure rate). Enable task chunking and split them into 30-minute sessions."
                ),
                category=cat,
                impact="high",
                supporting_metric=f"{cat} has {m_count} missed blocks ({m_rate}% missed rate)",
                action_type="split_tasks",
            )
        )

    # 4. Recommendation from Overload Days
    overload_days = stats.get("overload_days", [])
    if overload_days:
        num_overload = len(overload_days)
        recent_date = overload_days[0]["date"]
        missed_on_recent = overload_days[0]["missed_blocks_count"]
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Cap Maximum Daily Committed Hours",
                description=(
                    f"Detected {num_overload} overload day(s), including {recent_date} with {missed_on_recent} missed blocks. "
                    "Enforce a strict cap of 6.5 scheduled focus hours per day to prevent schedule collapse."
                ),
                category="workload_capacity",
                impact="high",
                supporting_metric=f"{num_overload} overload days detected with up to {missed_on_recent} missed blocks",
                action_type="capacity_cap",
            )
        )
    else:
        overall_comp = stats.get("overall_completion_rate_pct", 100)
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                title="Sustain Balanced Workload Distribution",
                description=(
                    f"Zero critical overload days detected with an overall completion rate of {overall_comp}%. "
                    "Continue protecting unscheduled buffer blocks across your work days."
                ),
                category="workload_capacity",
                impact="medium",
                supporting_metric=f"Overall completion rate is {overall_comp}% with 0 overload days",
                action_type="protect_buffers",
            )
        )

    return recommendations[:5]


# ---------------------------------------------------------------------------
# Gemini Generation with Strict Grounding Constraint
# ---------------------------------------------------------------------------

def generate_recommendations_from_stats(
    stats: Dict[str, Any],
    client: Optional[Any] = None,
) -> List[RecommendationItem]:
    """
    Sends ONLY the computed statistics to Gemini to generate 3-5 specific, non-generic recommendations.
    The prompt strictly forbids claims not supported by the supplied stats.
    """
    stats_json = json.dumps(stats, indent=2)

    prompt = (
        "You are an analytical productivity optimization expert.\n"
        "You are provided ONLY with the following user productivity statistics computed from their activity log:\n\n"
        f"=== COMPUTED PRODUCTIVITY STATS ===\n{stats_json}\n===================================\n\n"
        "CRITICAL INSTRUCTIONS & STRICT GROUNDING MANDATE:\n"
        "1. STRICT GROUNDING: You are strictly FORBIDDEN from making claims not directly supported by the supplied stats. "
        "Do not invent, guess, hallucinate, or cite any numbers, percentages, metrics, or claims that are not directly supported by the supplied stats above.\n"
        "2. NO GENERIC ADVICE: Do NOT provide generic advice like 'take breaks' or 'prioritize tasks'. Every recommendation "
        "must be specific and actionable, mentioning concrete numbers from the stats (e.g. 'You finish coding tasks 40% "
        "more often before noon; I moved 2 coding blocks earlier' or 'Status reports take 1.25x longer than planned; increase buffer by 15m').\n"
        "3. SUPPORTING METRICS: Every recommendation MUST cite the exact data point from the stats in its description and in its 'supporting_metric' field.\n"
        "4. OUTPUT QUANTITY: Generate between 3 and 5 concrete recommendations matching the schema.\n"
    )

    llm_client = client
    if llm_client is None:
        api_key = settings.GEMINI_API_KEY or "dummy_api_key_for_testing"
        llm_client = genai.Client(api_key=api_key)

    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecommendationListLLMResponse,
            temperature=0.1,
        )
        response = llm_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[prompt],
            config=config,
        )

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, RecommendationListLLMResponse) and parsed.recommendations:
            return parsed.recommendations
        elif isinstance(parsed, dict) and "recommendations" in parsed:
            return [RecommendationItem(**r) for r in parsed["recommendations"]]

        # If parsed is None, parse text
        text = getattr(response, "text", None)
        if text:
            data = json.loads(text)
            if isinstance(data, dict) and "recommendations" in data:
                return [RecommendationItem(**r) for r in data["recommendations"]]
            elif isinstance(data, list):
                return [RecommendationItem(**r) for r in data]
    except Exception:
        pass

    # Fallback to deterministic grounded recommendations directly from stats
    return _generate_fallback_grounded_recommendations(stats)


# ---------------------------------------------------------------------------
# Daily Cached Service Entrypoint
# ---------------------------------------------------------------------------

def get_daily_recommendations(
    db: Session,
    target_date_str: Optional[str] = None,
    force_refresh: bool = False,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Main entrypoint for GET /insights/recommendations.
    Computes stats from activity_log in plain Python, sends ONLY stats to Gemini,
    and caches the result per day.
    """
    now = datetime.now(timezone.utc)
    date_key = target_date_str or now.strftime("%Y-%m-%d")

    # 1. Check daily cache
    if not force_refresh and date_key in _DAILY_RECOMMENDATIONS_CACHE:
        cached = _DAILY_RECOMMENDATIONS_CACHE[date_key]
        return {
            "date": date_key,
            "generated_at": cached["generated_at"],
            "is_cached": True,
            "stats": cached["stats"],
            "recommendations": cached["recommendations"],
        }

    # 2. Query activity_log and tasks from DB
    logs = db.query(ActivityLog).all()
    tasks = db.query(Task).all()
    user_settings = db.query(UserSettings).first()

    # 3. Compute stats in plain Python
    stats = compute_activity_log_stats(
        logs=logs,
        tasks=tasks,
        settings_obj=user_settings,
        reference_time=now,
    )

    # 4. Generate 3-5 grounded recommendations via Gemini
    recommendations = generate_recommendations_from_stats(stats=stats, client=client)

    # 5. Cache result
    result_entry = {
        "date": date_key,
        "generated_at": now,
        "is_cached": False,
        "stats": stats,
        "recommendations": [r.model_dump() if hasattr(r, "model_dump") else r for r in recommendations],
    }
    _DAILY_RECOMMENDATIONS_CACHE[date_key] = result_entry

    return result_entry
