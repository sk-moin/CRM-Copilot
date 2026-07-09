"""RetrievedChunk model for tracking retrieved document chunks."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from packages.database.models.base import Base


class RetrievedChunk(Base):
    """Represents a chunk returned during a retrieval operation."""

    __tablename__ = "retrieved_chunks"

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

    trace_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("retrieval_traces.id"),
        nullable=False,
    )

    document_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id"),
        nullable=False,
    )

    chunk_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("document_chunks.id"),
        nullable=False,
    )

    rank = Column(
        Integer,
        nullable=False,
    )

    similarity_score = Column(
        Float,
        nullable=False,
    )

    chunk_preview = Column(
        String(500),
        nullable=False,
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

    trace = relationship(
        "RetrievalTrace",
        back_populates="retrieved_chunk_records",
    )

    document = relationship(
        "KnowledgeDocument",
        back_populates="retrieved_chunks",
    )

    chunk = relationship(
        "DocumentChunk",
        back_populates="retrievals",
    )

    __table_args__ = (
        CheckConstraint("rank > 0", name="ck_rank_positive"),
        CheckConstraint(
            "similarity_score >= 0 AND similarity_score <= 1",
            name="ck_similarity_score",
        ),
        Index("ix_retrieved_chunks_trace_id", "trace_id"),
        Index("ix_retrieved_chunks_document_id", "document_id"),
        Index("ix_retrieved_chunks_similarity_score", "similarity_score"),
        Index("ix_retrieved_chunks_trace_rank", "trace_id", "rank"),
    )

    def __repr__(self) -> str:
        return (
            f"<RetrievedChunk(id={self.id}, "
            f"rank={self.rank}, "
            f"similarity_score={self.similarity_score:.4f})>"
        )