"""Result model for document processing.

This module defines the output returned by the document processing pipeline.
It is a lightweight data class that summarizes the outcome of a processing
operation and is independent of FastAPI or SQLAlchemy models.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from packages.database.models.enums import DocumentProcessingStatus


@dataclass(slots=True)
class DocumentProcessingResult:
    """Result returned after processing a document.

    Attributes:
        document_id:
            ID of the processed KnowledgeDocument.
        chunk_count:
            Number of chunks generated for the document.
        status:
            Final processing status.
    """

    document_id: UUID
    chunk_count: int
    status: DocumentProcessingStatus