"""
Pydantic schemas for Knowledge Documents.

These schemas are used by the document management API and are independent
from SQLAlchemy models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentEnqueuedResponse(BaseModel):
    """Returned by upload once ingestion is a background job.

    There is no chunk count yet: nothing has been parsed. Poll
    `GET /documents/{id}/status` for progress.
    """

    document_id: UUID
    status: str
    job_id: str | None = Field(
        default=None,
        description=(
            "arq job id. Null only if the queue declined the job, which "
            "cannot currently happen: no explicit job id is supplied, so "
            "arq always generates a unique one."
        ),
    )


class DocumentStatusResponse(BaseModel):
    """Progress of a document's ingestion."""

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    status: str

    processing_started_at: datetime | None = None
    processed_at: datetime | None = None

    chunk_count: int = 0

    error_message: str | None = Field(
        default=None,
        description="Set only when status is FAILED.",
    )
