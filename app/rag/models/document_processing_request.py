"""Request model for document processing.

This module defines the input contract for the document processing pipeline.
It is a pure data class used by DocumentProcessingService and is independent
of FastAPI or SQLAlchemy models.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class DocumentProcessingRequest:
    """Input required to process a document.

    Attributes:
        tenant_id:
            Tenant that owns the document.
        organization_id:
            Organization associated with the document.
        owner_id:
            Optional user that uploaded or owns the document.
        title:
            Human-readable document title.
        filename:
            Original filename.
        storage_path:
            Absolute or relative path to the stored file.
        document_type:
            Logical document type (e.g. policy, manual, contract).
        source_type:
            Source of the document (e.g. upload, api, sync).
        mime_type:
            MIME type of the stored file.
        file_size:
            File size in bytes.
    """

    tenant_id: UUID
    organization_id: UUID
    owner_id: UUID | None

    title: str
    filename: str
    storage_path: str

    document_type: str
    source_type: str
    mime_type: str

    file_size: int