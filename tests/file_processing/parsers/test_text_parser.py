"""Tests for TextParser."""

from pathlib import Path

import pytest

from app.file_processing.parsers.text_parser import TextParser
from app.file_processing.models.extracted_document import ExtractedDocument


def test_can_parse_txt():
    """Parser should recognize .txt files."""
    assert TextParser.can_parse("sample.txt")
    assert TextParser.can_parse(Path("sample.TXT"))


def test_cannot_parse_other_extensions():
    """Parser should reject unsupported extensions."""
    assert not TextParser.can_parse("sample.pdf")
    assert not TextParser.can_parse("sample.docx")


def test_parse_text_file(tmp_path):
    """Parse a normal text file."""
    file_path = tmp_path / "sample.txt"
    content = "Hello World\nThis is a test."

    file_path.write_text(content, encoding="utf-8")

    document = TextParser.parse(file_path)

    assert isinstance(document, ExtractedDocument)
    assert document.text == content
    assert document.filename == "sample.txt"
    assert document.mime_type == "text/plain"


def test_parse_empty_file(tmp_path):
    """Parsing an empty file should succeed."""
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    document = TextParser.parse(file_path)

    assert document.text == ""
    assert document.filename == "empty.txt"


def test_parse_unicode_file(tmp_path):
    """Parser should preserve Unicode characters."""
    file_path = tmp_path / "unicode.txt"

    content = "こんにちは\nمرحبا\nनमस्ते\n😊"

    file_path.write_text(content, encoding="utf-8")

    document = TextParser.parse(file_path)

    assert document.text == content


def test_parse_missing_file():
    """Missing files should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        TextParser.parse("does_not_exist.txt")