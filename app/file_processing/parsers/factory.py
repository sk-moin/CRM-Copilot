"""Factory for selecting the appropriate document parser."""

from __future__ import annotations

from pathlib import Path

from app.file_processing.parsers.base import DocumentParser
from app.file_processing.parsers.docx_parser import DOCXParser
from app.file_processing.parsers.markdown_parser import MarkdownParser
from app.file_processing.parsers.pdf_parser import PDFParser
from app.file_processing.parsers.text_parser import TextParser


class ParserFactory:
    """Factory for creating document parser instances."""

    _parsers = (
        PDFParser,
        DOCXParser,
        MarkdownParser,
        TextParser,
    )

    @classmethod
    def get_parser(cls, file_path: str | Path) -> DocumentParser:
        """Return a parser capable of handling the supplied file."""

        for parser_cls in cls._parsers:
            if parser_cls.can_parse(file_path):
                return parser_cls()

        suffix = Path(file_path).suffix.lower() or "<no extension>"

        raise ValueError(
            f"Unsupported file type: {suffix}"
        )