from __future__ import annotations

import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    UUID as PGUUID,
    func,
)
from sqlalchemy.orm import relationship

from packages.database.models.base import Base


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    org_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
    )

    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    status = Column(
        SAEnum(
            ConversationStatus,
            name="conversation_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ConversationStatus.ACTIVE,
        server_default=ConversationStatus.ACTIVE.value,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )

    retrieval_traces = relationship(
        "RetrievalTrace",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_conversation_tenant_user",
            "tenant_id",
            "user_id",
        ),
        Index(
            "ix_conversation_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_conversation_created_at",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"status={self.status})>"
        )