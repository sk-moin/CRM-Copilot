"""
Pydantic schemas for Knowledge Documents.

These schemas are used by the document management API and are independent
from SQLAlchemy models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.database.models.enums import DocumentProcessingStatus


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading a document."""

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    title: str
    filename: str
    processing_status: DocumentProcessingStatus
    message: str


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #


class DocumentSearchRequest(BaseModel):
    """Semantic document search request."""

    query: str = Field(
        min_length=1,
        max_length=4000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    document_id: UUID | None = None


class SearchResult(BaseModel):
    """Single retrieved chunk."""

    chunk_id: UUID
    document_id: UUID

    chunk_index: int

    content: str

    similarity_score: float

    metadata: dict = Field(
        default_factory=dict,
    )


class DocumentSearchResponse(BaseModel):
    """Semantic search response."""

    results: list[SearchResult]

    retrieved_chunks: int


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #


class DocumentResponse(BaseModel):
    """Knowledge document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    tenant_id: UUID

    organization_id: UUID

    owner_id: UUID | None

    title: str

    filename: str

    document_type: str

    source_type: str

    mime_type: str

    file_size: int

    chunk_count: int

    processing_status: DocumentProcessingStatus

    storage_path: str

    created_at: datetime

    updated_at: datetime

    processed_at: datetime | None

    error_message: str | None


# --------------------------------------------------------------------------- #
# Document List
# --------------------------------------------------------------------------- #


class DocumentListResponse(BaseModel):
    """Paginated document list."""

    documents: list[DocumentResponse]

    total: int


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #


class DocumentDeleteResponse(BaseModel):
    """Delete response."""

    success: bool

    message: str


# --------------------------------------------------------------------------- #
# Reindex
# --------------------------------------------------------------------------- #


class DocumentReindexResponse(BaseModel):
    """Reindex response."""

    document_id: UUID

    processing_status: DocumentProcessingStatus

    message: str


# --------------------------------------------------------------------------- #
# Chunk
# --------------------------------------------------------------------------- #


class ChunkResponse(BaseModel):
    """Document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    chunk_index: int

    content: str

    start_char: int

    end_char: int

    token_count: int

    metadata: dict


class DocumentChunksResponse(BaseModel):
    """All chunks for a document."""

    document_id: UUID

    chunks: list[ChunkResponse]