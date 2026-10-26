import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), nullable=True)
    sender = Column(String(32), nullable=False)  # user, agent, system
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    proposal_id = Column(String(36), ForeignKey("plan_proposals.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    proposal = relationship("PlanProposal", back_populates="messages")
