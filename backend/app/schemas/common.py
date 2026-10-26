from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="API operational status")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current UTC timestamp")
    database: str = Field(..., description="Database connection health")
