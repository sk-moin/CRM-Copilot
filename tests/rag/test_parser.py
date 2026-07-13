"""
tests/rag/test_parser.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.exceptions import (
    DocumentParsingError,
    UnsupportedDocumentTypeError,
)
from app.rag.loaders.parser import (
    DocumentParser,
    ExtractedDocument,
    create_document_parser,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def parser() -> DocumentParser:
    return create_document_parser()


@pytest.fixture
def txt_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.txt"
    path.write_text(
        "Customer Relationship Management",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def md_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.md"
    path.write_text(
        "# CRM\n\nMarkdown content.",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def unsupported_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.xyz"
    path.write_text(
        "unsupported",
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- #
# TXT / Markdown Parsing
# --------------------------------------------------------------------------- #

def test_parse_txt(
    parser: DocumentParser,
    txt_file: Path,
):
    document = parser.parse(txt_file)

    assert isinstance(document, ExtractedDocument)

    assert (
        document.content
        == "Customer Relationship Management"
    )

    assert document.filename == "sample.txt"

    assert document.mime_type == "text/plain"


def test_parse_markdown(
    parser: DocumentParser,
    md_file: Path,
):
    document = parser.parse(md_file)

    assert isinstance(document, ExtractedDocument)

    assert "# CRM" in document.content
    assert "Markdown content." in document.content

    assert document.filename == "sample.md"

    assert document.mime_type == "text/markdown"


# --------------------------------------------------------------------------- #
# Error Handling
# --------------------------------------------------------------------------- #

def test_parse_missing_file(
    parser: DocumentParser,
    tmp_path: Path,
):
    missing = tmp_path / "missing.txt"

    with pytest.raises(DocumentParsingError):
        parser.parse(missing)


def test_parse_unsupported_file_type(
    parser: DocumentParser,
    unsupported_file: Path,
):
    with pytest.raises(
        UnsupportedDocumentTypeError
    ):
        parser.parse(unsupported_file)


# --------------------------------------------------------------------------- #
# ExtractedDocument Fields
# --------------------------------------------------------------------------- #

def test_document_fields(
    parser: DocumentParser,
    txt_file: Path,
):
    document = parser.parse(txt_file)

    assert document.filename == "sample.txt"

    assert document.mime_type == "text/plain"

    assert document.page_count is None

    assert document.title is None

    assert document.author is None

    assert document.source_type is None


def test_parse_empty_text_file(
    parser: DocumentParser,
    tmp_path: Path,
):
    empty = tmp_path / "empty.txt"

    empty.write_text(
        "",
        encoding="utf-8",
    )

    document = parser.parse(empty)

    assert isinstance(document, ExtractedDocument)

    assert document.content == ""

    assert document.filename == "empty.txt"

    assert document.mime_type == "text/plain"


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def test_create_document_parser():
    parser = create_document_parser()

    assert isinstance(
        parser,
        DocumentParser,
    )


# --------------------------------------------------------------------------- #
# Additional Parser Scenarios
# --------------------------------------------------------------------------- #

def test_parse_accepts_path_object(
    parser: DocumentParser,
    txt_file: Path,
):
    document = parser.parse(txt_file)

    assert isinstance(document, ExtractedDocument)

    assert (
        document.content
        == "Customer Relationship Management"
    )


def test_parse_returns_string_content(
    parser: DocumentParser,
    txt_file: Path,
):
    document = parser.parse(txt_file)

    assert isinstance(
        document.content,
        str,
    )


def test_parse_preserves_whitespace(
    parser: DocumentParser,
    tmp_path: Path,
):
    path = tmp_path / "whitespace.txt"

    path.write_text(
        "Line 1\n\nLine 2\n\nLine 3",
        encoding="utf-8",
    )

    document = parser.parse(path)

    assert (
        document.content
        == "Line 1\n\nLine 2\n\nLine 3"
    )


# --------------------------------------------------------------------------- #
# ExtractedDocument Dataclass
# --------------------------------------------------------------------------- #

def test_extracted_document_dataclass():
    document = ExtractedDocument(
        content="Example content",
        filename="example.txt",
        mime_type="text/plain",
    )

    assert (
        document.content
        == "Example content"
    )

    assert (
        document.filename
        == "example.txt"
    )

    assert (
        document.mime_type
        == "text/plain"
    )

    assert document.page_count is None

    assert document.title is None

    assert document.author is None

    assert document.source_type is None