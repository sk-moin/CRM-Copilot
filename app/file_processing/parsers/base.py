"""Abstract base class for document parsers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from app.file_processing.models.extracted_document import ExtractedDocument


class DocumentParser(ABC):
    """Abstract interface for document parsers.

    All concrete parsers must implement the ``parse`` method
    which returns an ``ExtractedDocument`` instance.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset()

    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        """Check if this parser supports the given file."""
        path = Path(file_path)
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS

    @staticmethod
    @abstractmethod
    def parse(file_path: Union[str, Path]) -> ExtractedDocument:
        """Parse a document file and return extracted content.

        Args:
            file_path: Path to the document file

        Returns:
            ExtractedDocument containing the parsed text and metadata

        Raises:
            FileNotFoundError: If the file does not exist
            DocumentParsingError: If the file cannot be parsed
        """
        ...