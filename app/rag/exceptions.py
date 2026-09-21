"""
Custom exceptions for the RAG pipeline.
"""

from __future__ import annotations


class RAGError(Exception):
    """Base exception for the RAG module."""


class DocumentProcessingError(RAGError):
    """Raised when document processing fails."""


class DocumentNotFoundError(DocumentProcessingError):
    """The document does not exist, or does not belong to this tenant.

    Distinct because there is nothing to record a failure against: a job
    naming another tenant's document must leave no trace on it at all.
    """


class UnsupportedDocumentTypeError(DocumentProcessingError):
    """Raised when an unsupported document type is provided."""


class DocumentParsingError(DocumentProcessingError):
    """Raised when a document cannot be parsed."""


class EmptyDocumentError(DocumentProcessingError):
    """Raised when no readable content is extracted from a document."""


class ChunkingError(DocumentProcessingError):
    """Raised when document chunking fails."""


class EmbeddingError(RAGError):
    """Raised when embedding generation fails."""


class VectorStoreError(RAGError):
    """Raised when a vector store operation fails."""


class RetrievalError(RAGError):
    """Raised when retrieval fails."""


class RAGGenerationError(RAGError):
    """Raised when answer generation fails."""