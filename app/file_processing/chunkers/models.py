"""Chunker data models.

This module defines pure-Python data structures used by the document chunking
pipeline. These models are intentionally independent of the database layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextChunk:
    """A chunk of text produced by a TextChunker.

    Attributes:
        text: Normalized text content for the chunk.
        chunk_index: Zero-based position of the chunk within the document.
        start_char: Inclusive character offset in the source document.
        end_char: Exclusive character offset in the source document.
        token_count: Approximate token count (len(text) // 4).
        metadata: Arbitrary metadata for downstream processing.
    """

    text: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)