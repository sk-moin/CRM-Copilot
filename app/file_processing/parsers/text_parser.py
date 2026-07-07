"""Plain text document parser."""

import re
from pathlib import Path
from typing import Union

from app.file_processing.exceptions import DocumentParsingError
from app.file_processing.models.extracted_document import ExtractedDocument
from .base import DocumentParser


class TextParser(DocumentParser):
    """Parser for plain text files."""

    SUPPORTED_EXTENSIONS = frozenset({".txt"})

    @staticmethod
    def parse(file_path: Union[str, Path]) -> ExtractedDocument:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {path}")

        # Try UTF-8 first, fall back to latin-1 for encoding compatibility
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        except OSError as exc:
            raise DocumentParsingError(
                f"Failed to read text file: {exc}",
                source_type="Text",
            ) from exc

        # Normalize text
        # Normalize line endings to \n
        text = re.sub(r"\r\n|\r", "\n", text)
        # Remove null bytes
        text = text.replace("\x00", "")
        # Trim whitespace
        text = text.strip()


        return ExtractedDocument(
            text=text,
            filename=path.name,
            mime_type="text/plain",
            page_count=1,
            source_type="TEXT",
        )