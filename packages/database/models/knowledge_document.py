"""KnowledgeDocument model."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from packages.database.models.base import Base
from packages.database.models.enums import DocumentProcessingStatus
import uuid

class KnowledgeDocument(Base):
    """Knowledge document uploaded for retrieval and RAG."""

    __tablename__ = "knowledge_documents"

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
    org_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=True)

    document_type = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)

    file_size = Column(BigInteger, nullable=False)

    processing_status = Column(
        Enum(DocumentProcessingStatus, name="processing_status", create_type=False),
        nullable=False,
        default=DocumentProcessingStatus.UPLOADED,
    )

    processing_started_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    error_message = Column(Text, nullable=True)

    chunk_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    retrieved_chunks = relationship(
        "RetrievedChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_knowledge_documents_tenant_id", "tenant_id"),
        Index("ix_knowledge_documents_organization_id", "org_id"),
        Index("ix_knowledge_documents_status", "processing_status"),
        Index(
            "ix_knowledge_documents_tenant_status",
            "tenant_id",
            "processing_status",
        ),
    )
