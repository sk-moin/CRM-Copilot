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

    text: str
    filename: str
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    source_type: Optional[str] = None
