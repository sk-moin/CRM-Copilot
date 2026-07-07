"""Markdown document parser."""

import re
from pathlib import Path
from typing import Union

from app.file_processing.exceptions import DocumentParsingError
from app.file_processing.models.extracted_document import ExtractedDocument
from .base import DocumentParser


class MarkdownParser(DocumentParser):
    """Parser for Markdown files."""

    SUPPORTED_EXTENSIONS = frozenset({".md", ".markdown"})

    @staticmethod
    def parse(file_path: Union[str, Path]) -> ExtractedDocument:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Markdown file not found: {path}")

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fall back to latin-1 for broader compatibility
            text = path.read_text(encoding="latin-1")
        except OSError as exc:
            raise DocumentParsingError(
                f"Failed to read Markdown file: {exc}",
                source_type="Markdown",
            ) from exc

        # Extract title from first heading if exists
        title = None
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Normalize text
        # Normalize line endings to \n
        text = re.sub(r"\r\n|\r", "\n", text)
        # Remove null bytes
        text = text.replace("\x00", "")
        # Trim leading/trailing whitespace
        text = text.strip()

        if not text:
            raise DocumentParsingError(
                "Markdown document contains no text.",
                source_type="Markdown",
            )

        return ExtractedDocument(
            text=text,
            filename=path.name,
            mime_type="text/markdown",
            title=title,
            source_type="Markdown",
        )