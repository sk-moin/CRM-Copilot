"""ExtractedDocument model for parsed document content.

This is a pure data class used by the parsing layer.
It is NOT a database model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedDocument:
    """Result of parsing a document file.

    Contains the raw extracted text and optional metadata.
    The parser layer is responsible only for extraction;
    downstream processing (tokenization, chunking) belongs elsewhere.
    """

    content: str
    filename: str

    mime_type: str | None = None
    page_count: int | None = None
    title: str | None = None
    author: str | None = None
    source_type: str | None = None
