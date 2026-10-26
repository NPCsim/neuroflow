from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.common import HealthResponse

app = FastAPI(
    title="NeuroFlow API",
    description="Deterministic AI Productivity Scheduler Backend",
    version="1.0.0",
)

from app.routers.workload import router as workload_router
from app.routers.goals import router as goals_router
from app.routers.agent import router as agent_router
from app.routers.insights import router as insights_router
from app.routers.demo import router as demo_router

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workload_router)
app.include_router(goals_router)
app.include_router(agent_router)
app.include_router(insights_router)
app.include_router(demo_router)



@app.get("/", tags=["System"])
def root():
    """Root endpoint returning service identity and helpful links."""
    return {
        "app": "NeuroFlow API",
        "status": "online",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend status and database connectivity."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": db_status},
        )

    return HealthResponse(
        status="ok",
        app="NeuroFlow API",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        database=db_status,
    )
