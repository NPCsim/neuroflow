import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanProposal(Base):
    __tablename__ = "plan_proposals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="draft_pending")  # draft_pending, approved, rejected, reverted
    summary = Column(String(255), nullable=False)
    diff_payload = Column(JSON, nullable=False, default=dict)
    snapshot_before = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    messages = relationship("ChatMessage", back_populates="proposal")
