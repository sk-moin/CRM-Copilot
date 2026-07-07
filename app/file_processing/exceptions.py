"""Exceptions for the file processing module."""


class DocumentParsingError(Exception):
    """Raised when a document cannot be parsed."""

    def __init__(self, message: str, source_type: str | None = None):
        self.source_type = source_type
        super().__init__(message)


class UnsupportedFileTypeError(DocumentParsingError):
    """Raised when attempting to parse an unsupported file type."""

    def __init__(self, file_extension: str):
        self.file_extension = file_extension
        super().__init__(
            f"Unsupported file type: {file_extension}",
            source_type=file_extension
        )

class ParserNotAvailableError(DocumentParsingError):
    """Raised when an optional parser dependency is not installed."""
    
    def __init__(self, parser_name: str):
        self.parser_name = parser_name
        super().__init__(
            f"Parser '{parser_name}' is not available. Please install the required dependencies.",
            source_type=parser_name
        )