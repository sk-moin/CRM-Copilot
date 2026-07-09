"""Pydantic schemas for RetrievalTrace."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.database.models.retrieval_trace import RetrievalTraceStatus


class RetrievalTraceBase(BaseModel):
    """Shared RetrievalTrace fields."""

    conversation_id: UUID | None = None
    query: str
    embedding_model: str | None = None
    vector_store: str | None = None
    embedding_latency_ms: float | None = None
    retrieval_latency_ms: float | None = None
    total_latency_ms: float | None = None
    retrieved_chunks: int = Field(default=0, ge=0)
    status: RetrievalTraceStatus = RetrievalTraceStatus.SUCCESS
    error_message: str | None = None
    retrieval_metadata: dict[str, Any] | None = None


class RetrievalTraceCreate(RetrievalTraceBase):
    """Schema used when creating a retrieval trace."""


class RetrievalTraceUpdate(BaseModel):
    """Schema used when updating a retrieval trace."""

    embedding_model: str | None = None
    vector_store: str | None = None
    embedding_latency_ms: float | None = None
    retrieval_latency_ms: float | None = None
    total_latency_ms: float | None = None
    retrieved_chunks: int | None = Field(default=None, ge=0)
    status: RetrievalTraceStatus | None = None
    error_message: str | None = None
    retrieval_metadata: dict[str, Any] | None = None


class RetrievalTraceRead(RetrievalTraceBase):
    """Schema returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class RetrievalTraceListResponse(BaseModel):
    """Collection of retrieval traces."""

    items: list[RetrievalTraceRead]
    total: int