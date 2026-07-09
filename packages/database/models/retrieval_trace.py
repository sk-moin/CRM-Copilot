"""RetrievalTrace model for tracking RAG pipeline retrievals."""

from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from packages.database.models.base import Base


class RetrievalTraceStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class RetrievalTrace(Base):
    """Trace of every retrieval performed by the RAG pipeline."""

    __tablename__ = "retrieval_traces"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id"),
        nullable=False,
    )

    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation.id"),
        nullable=True,
    )

    query = Column(
        Text,
        nullable=False,
    )

    embedding_model = Column(
        String(255),
        nullable=True,
    )

    vector_store = Column(
        String(100),
        nullable=True,
    )

    embedding_latency_ms = Column(
        Float,
        nullable=True,
    )

    retrieval_latency_ms = Column(
        Float,
        nullable=True,
    )

    total_latency_ms = Column(
        Float,
        nullable=True,
    )

    retrieved_chunks = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    status = Column(
        SAEnum(
            RetrievalTraceStatus,
            name="retrieval_trace_status",
            values_callable=lambda enum: [e.value for e in enum],
            create_type=False,
        ),
        nullable=False,
        default=RetrievalTraceStatus.SUCCESS,
        server_default=RetrievalTraceStatus.SUCCESS.value,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    retrieval_metadata = Column(
        JSON,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    retrieved_chunk_records = relationship(
        "RetrievedChunk",
        back_populates="trace",
        cascade="all, delete-orphan",
    )
    
    conversation = relationship(
        "Conversation",
        back_populates="retrieval_traces",
    )

    __table_args__ = (
        Index("ix_retrieval_traces_created_at", "created_at"),
        Index("ix_retrieval_traces_conversation_id", "conversation_id"),
        Index("ix_retrieval_traces_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<RetrievalTrace(id={self.id}, "
            f"status={self.status}, "
            f"retrieved_chunks={self.retrieved_chunks})>"
        )