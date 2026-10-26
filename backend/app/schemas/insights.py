from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RecommendationItem(BaseModel):
    id: str = Field(..., description="Unique recommendation ID")
    title: str = Field(..., description="Concise, non-generic recommendation title")
    description: str = Field(
        ...,
        description="Actionable recommendation citing specific data (e.g. 'You finish coding tasks 40% more often before noon; I moved 2 coding blocks earlier')",
    )
    category: str = Field(..., description="Category or domain targeted (e.g. 'coding', 'study', 'time_management')")
    impact: str = Field("high", description="Estimated impact: high, medium, or low")
    supporting_metric: str = Field(
        ...,
        description="The exact quantitative metric from the supplied stats justifying this recommendation",
    )
    action_type: Optional[str] = Field(None, description="Actionable strategy type (e.g. 'reschedule_morning', 'buffer_boost')")


class RecommendationListLLMResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3 to 5 specific, non-generic recommendations strictly grounded in the supplied stats",
    )


class InsightsRecommendationsResponse(BaseModel):
    date: str = Field(..., description="Date key for caching (YYYY-MM-DD)")
    generated_at: datetime = Field(..., description="Timestamp of when recommendations were generated or retrieved")
    is_cached: bool = Field(False, description="True if response was served from daily cache")
    stats: Dict[str, Any] = Field(..., description="Computed activity log stats (categories, time of day, ratios, overload days)")
    recommendations: List[RecommendationItem] = Field(..., description="3-5 specific, grounded recommendations")

    model_config = ConfigDict(populate_by_name=True)
