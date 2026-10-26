from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.insights import InsightsRecommendationsResponse
from app.services.insights_service import get_daily_recommendations

router = APIRouter(prefix="/insights", tags=["Productivity Insights"])


@router.get(
    "/recommendations",
    response_model=InsightsRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized productivity recommendations derived from activity log statistics",
    description=(
        "Computes stats from activity_log in plain Python (completion rate by category and time of day, "
        "planned vs actual duration ratio, most-missed task types, overload days), sends ONLY the stats "
        "to Gemini with strict grounding (forbidding unsupported claims), and caches recommendations per day."
    ),
)
def get_recommendations_endpoint(
    date: Optional[str] = Query(None, description="Date key for caching (YYYY-MM-DD), defaults to today UTC"),
    force_refresh: bool = Query(False, description="Set true to bypass daily cache and regenerate recommendations"),
    db: Session = Depends(get_db),
):
    result = get_daily_recommendations(
        db=db,
        target_date_str=date,
        force_refresh=force_refresh,
    )
    return InsightsRecommendationsResponse(
        date=result["date"],
        generated_at=result["generated_at"],
        is_cached=result["is_cached"],
        stats=result["stats"],
        recommendations=result["recommendations"],
    )
