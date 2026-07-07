"""PDF document parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

from app.file_processing.exceptions import (
    DocumentParsingError,
    ParserNotAvailableError,
)
from app.file_processing.models.extracted_document import ExtractedDocument

from .base import DocumentParser


class PDFParser(DocumentParser):
    """Parser for PDF documents."""

    SUPPORTED_EXTENSIONS = frozenset({".pdf"})

    @staticmethod
    def parse(file_path: Union[str, Path]) -> ExtractedDocument:
        """Extract text and metadata from a PDF file."""
        path = Path(file_path)

        if PdfReader is None:
            raise ParserNotAvailableError("pypdf")

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        try:
            reader = PdfReader(path)
        except Exception as exc:
            raise DocumentParsingError(
                f"Failed to read PDF file: {exc}"
            ) from exc

        metadata = reader.metadata

        text_parts: list[str] = []

        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception:
                continue

        full_text = "\n".join(text_parts)

        full_text = re.sub(r"\r\n|\r", "\n", full_text)
        full_text = full_text.replace("\x00", "")
        full_text = full_text.strip()

        return ExtractedDocument(
            text=full_text,
            filename=path.name,
            mime_type="application/pdf",
            page_count=max(1, len(reader.pages)),
            title=getattr(metadata, "title", None) if metadata else None,
            author=getattr(metadata, "author", None) if metadata else None,
            source_type="PDF",
        )