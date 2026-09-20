"""DocumentChunk - one embedded slice of a knowledge document.

The column and index declarations here mirror the live schema exactly,
including the pgvector index. They did not used to: several indexes and
foreign keys existed only in migrations, so `alembic revision --autogenerate`
proposed dropping them, which made autogenerate unusable and dangerous.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from packages.database.models.base import Base
from packages.database.models.knowledge_document import KnowledgeDocument  # noqa: F401


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)

    token_count = Column(Integer, nullable=False)

    # 384 dimensions: BAAI/bge-small and all-MiniLM-L6-v2 both produce that.
    # Changing the embedding model means a migration and a full re-embed.
    embedding = Column(Vector(384), nullable=True)

    chunk_metadata = Column("metadata", JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    start_char = Column(Integer, nullable=True)

    end_char = Column(Integer, nullable=True)

    # Relationships
    document = relationship("KnowledgeDocument", back_populates="chunks")

    retrievals = relationship(
        "RetrievedChunk",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_document_chunks_chunk_index", "chunk_index"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_tenant_id", "tenant_id"),
        Index("ix_document_chunks_tenant_document", "tenant_id", "document_id"),
        # Approximate nearest-neighbour index for cosine similarity search.
        # Dropping this silently turns every retrieval into a sequential scan.
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
