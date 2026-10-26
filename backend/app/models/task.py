import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    goal_id = Column(String(36), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=False, default=60)
    remaining_duration_minutes = Column(Integer, nullable=False, default=60)
    priority = Column(String(32), nullable=False, default="normal")  # urgent_important, important, normal, low
    deadline = Column(DateTime(timezone=True), nullable=True)
    is_splittable = Column(Boolean, nullable=False, default=True)
    min_chunk_minutes = Column(Integer, nullable=False, default=30)
    status = Column(String(32), nullable=False, default="pending")  # pending, scheduled, completed, missed, cancelled
    carry_over_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    goal = relationship("Goal", back_populates="tasks")
    schedule_blocks = relationship("ScheduleBlock", back_populates="task", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="task", cascade="all, delete-orphan")
