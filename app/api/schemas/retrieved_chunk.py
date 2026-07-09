"""Pydantic schemas for RetrievedChunk."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievedChunkBase(BaseModel):
    """Shared RetrievedChunk fields."""

    trace_id: UUID
    document_id: UUID
    chunk_id: UUID
    rank: int = Field(..., gt=0)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    chunk_preview: str
    retrieval_metadata: dict[str, Any] | None = None


class RetrievedChunkCreate(RetrievedChunkBase):
    """Schema used when creating a retrieved chunk."""


class RetrievedChunkRead(RetrievedChunkBase):
    """Schema returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class RetrievedChunkListResponse(BaseModel):
    """Collection of retrieved chunks."""

    items: list[RetrievedChunkRead]
    total: int