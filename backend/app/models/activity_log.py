import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    schedule_block_id = Column(String(36), ForeignKey("schedule_blocks.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(64), nullable=False, default="missed")
    entity_type = Column(String(64), nullable=False, default="schedule_block")
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    task = relationship("Task", back_populates="activity_logs")
    schedule_block = relationship("ScheduleBlock", back_populates="activity_logs")

    @property
    def message(self) -> str:
        return self.description or ""

    @property
    def status(self) -> str:
        return self.action

    def __repr__(self) -> str:
        return f"<ActivityLog {self.id} action={self.action} task_id={self.task_id} block_id={self.schedule_block_id}>"
