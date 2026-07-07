from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from packages.database.models.base import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import JSON
from pgvector.sqlalchemy import Vector
from packages.database.models.knowledge_document import KnowledgeDocument
import uuid

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    chunk_metadata = Column("metadata",JSON,nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)

    # Relationship
    document = relationship("KnowledgeDocument", back_populates="chunks")