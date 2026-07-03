from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UUID as PGUUID,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from packages.database.models.base import Base


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(Base):
    __tablename__ = "message"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        SAEnum(
            MessageRole,
            values_callable=lambda obj: [e.value for e in obj],
            name="message_role",
        ),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    # Provider metadata
    model = Column(
        String(100),
        nullable=True,
    )

    prompt_tokens = Column(
        Integer,
        nullable=True,
    )

    completion_tokens = Column(
        Integer,
        nullable=True,
    )

    total_tokens = Column(
        Integer,
        nullable=True,
    )

    latency_ms = Column(
        Integer,
        nullable=True,
    )

    finish_reason = Column(
        String(50),
        nullable=True,
    )

    message_metadata = Column(
        JSONB,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_message_conversation",
            "conversation_id",
            "created_at",
        ),
        Index(
            "ix_message_tenant",
            "tenant_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Message("
            f"id={self.id}, "
            f"role={self.role}, "
            f"conversation_id={self.conversation_id})>"
        )