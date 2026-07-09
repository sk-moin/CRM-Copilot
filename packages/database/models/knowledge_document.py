"""KnowledgeDocument model."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from packages.database.models.base import Base
from packages.database.models.enums import DocumentProcessingStatus
import uuid

class KnowledgeDocument(Base):
    """Knowledge document uploaded for retrieval and RAG."""

    __tablename__ = "knowledge_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    organization_id = Column(PGUUID(as_uuid=True), nullable=False)
    owner_id = Column(PGUUID(as_uuid=True), nullable=True)

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

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
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