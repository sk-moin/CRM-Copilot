"""Base abstract interface for text chunking."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.file_processing.chunkers.models import TextChunk
from app.file_processing.models.extracted_document import ExtractedDocument


class TextChunker(ABC):
    """Abstract base class for all text chunking strategies."""

    @abstractmethod
    def chunk(self, document: ExtractedDocument) -> list[TextChunk]:
        """Split a document into ordered text chunks.

        Args:
            document: Parsed document to chunk.

        Returns:
            A list of TextChunk objects. Returns an empty list for an empty
            document.
        """
        raise NotImplementedError