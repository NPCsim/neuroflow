import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timezone = Column(String(64), nullable=False, default="UTC")
    work_start_time = Column(String(10), nullable=False, default="09:00")
    work_end_time = Column(String(10), nullable=False, default="17:00")
    work_days = Column(JSON, nullable=False, default=list)  # e.g., [0, 1, 2, 3, 4] for Mon-Fri
    buffer_minutes = Column(Integer, nullable=False, default=10)
    min_chunk_minutes = Column(Integer, nullable=False, default=30)
    max_chunk_minutes = Column(Integer, nullable=False, default=120)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
