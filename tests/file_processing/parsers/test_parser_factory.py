"""Tests for ParserFactory."""

from pathlib import Path

import pytest

from app.file_processing.parsers.factory import ParserFactory
from app.file_processing.parsers.pdf_parser import PDFParser
from app.file_processing.parsers.docx_parser import DOCXParser
from app.file_processing.parsers.text_parser import TextParser


def test_get_pdf_parser():
    """Factory should return PDFParser."""
    parser = ParserFactory.get_parser("document.pdf")

    assert isinstance(parser, PDFParser)


def test_get_docx_parser():
    """Factory should return DOCXParser."""
    parser = ParserFactory.get_parser("document.docx")

    assert isinstance(parser, DOCXParser)


def test_get_text_parser():
    """Factory should return TextParser."""
    parser = ParserFactory.get_parser("document.txt")

    assert isinstance(parser, TextParser)


def test_get_parser_with_path_object():
    """Factory should accept pathlib.Path."""
    parser = ParserFactory.get_parser(Path("notes.txt"))

    assert isinstance(parser, TextParser)


@pytest.mark.parametrize(
    "extension",
    [
        "pdf",
        "PDF",
        "Pdf",
        "pDf",
    ],
)
def test_extension_case_insensitive(extension):
    """Extensions should be matched case-insensitively."""
    parser = ParserFactory.get_parser(f"file.{extension}")

    assert isinstance(parser, PDFParser)


@pytest.mark.parametrize(
    "filename",
    [
        "image.png",
        "archive.zip",
        "video.mp4",
        "music.mp3",
        "spreadsheet.xlsx",
        "presentation.pptx",
        "unknown",
    ],
)
def test_unsupported_extension(filename):
    """Unsupported extensions should raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        ParserFactory.get_parser(filename)