import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=1)
    total_chunks = Column(Integer, nullable=False, default=1)
    is_completed = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="planned")  # planned, completed, missed
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    task = relationship("Task", back_populates="schedule_blocks")
    activity_logs = relationship("ActivityLog", back_populates="schedule_block")
