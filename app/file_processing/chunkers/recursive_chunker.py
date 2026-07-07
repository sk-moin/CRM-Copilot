"""Recursive text chunking implementation.

This module implements a RecursiveTextChunker that splits an
ExtractedDocument into a list of TextChunk objects using a prioritized
list of separators.
"""

from __future__ import annotations

import re
from typing import List

from app.file_processing.models.extracted_document import ExtractedDocument

from .base import TextChunker
from .models import TextChunk


class RecursiveTextChunker(TextChunker):
    """Recursive text chunker with configurable chunk size and overlap."""

    _DEFAULT_CHUNK_SIZE = 1000
    _DEFAULT_CHUNK_OVERLAP = 200

    def __init__(
        self,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize chunk text."""
        text = text.strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.replace("\x00", "")
        return text

    @staticmethod
    def _find_last_separator(
        text: str,
        start: int,
        length: int,
    ) -> tuple[int, str]:
        """Find the last suitable separator within the given window."""

        separators = ["\n\n", "\n", ". ", " "]

        search_end = min(start + length, len(text))

        best_index = -1
        best_separator = ""

        for sep in separators:
            idx = text.rfind(sep, start, search_end)
            if idx > best_index:
                best_index = idx
                best_separator = sep

        if best_index != -1:
            return best_index + len(best_separator), best_separator

        return search_end, ""

    @staticmethod
    def _token_count(text: str) -> int:
        """Approximate token count."""
        return len(text) // 4

    def chunk(self, document: ExtractedDocument) -> List[TextChunk]:
        """Split a document into ordered text chunks."""

        raw_text = document.text

        if not raw_text or not raw_text.strip():
            return []

        raw_text = self._normalize(raw_text)

        # Fast path for small documents.
        if len(raw_text) <= self.chunk_size:
            return [
                TextChunk(
                    text=raw_text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(raw_text),
                    token_count=self._token_count(raw_text),
                    metadata={
                        "chunk_size": self.chunk_size,
                        "chunk_overlap": self.chunk_overlap,
                    },
                )
            ]

        chunks: List[TextChunk] = []
        current_pos = 0

        while current_pos < len(raw_text):
            slice_end = min(
                current_pos + self.chunk_size,
                len(raw_text),
            )

            chunk_end, _ = self._find_last_separator(
                raw_text,
                current_pos,
                slice_end - current_pos,
            )

            if chunk_end <= current_pos:
                chunk_end = slice_end

            normalized = self._normalize(raw_text[current_pos:chunk_end])

            if normalized:
                chunks.append(
                    TextChunk(
                        text=normalized,
                        chunk_index=len(chunks),
                        start_char=current_pos,
                        end_char=chunk_end,
                        token_count=self._token_count(normalized),
                        metadata={
                            "chunk_size": self.chunk_size,
                            "chunk_overlap": self.chunk_overlap,
                        },
                    )
                )

            if chunk_end >= len(raw_text):
                break

            next_pos = max(
                chunk_end - self.chunk_overlap,
                current_pos + 1,
            )

            current_pos = next_pos

        return chunks