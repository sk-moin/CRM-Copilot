"""Tests for ExtractedDocument."""

from app.file_processing.models.extracted_document import ExtractedDocument


def test_create_extracted_document():
    """Create an ExtractedDocument with all fields."""
    doc = ExtractedDocument(
        text="Hello World",
        filename="sample.txt",
        mime_type="text/plain",
        page_count=1,
        title="Sample",
        author="Moin",
        source_type="upload",
    )

    assert doc.text == "Hello World"
    assert doc.filename == "sample.txt"
    assert doc.mime_type == "text/plain"
    assert doc.page_count == 1
    assert doc.title == "Sample"
    assert doc.author == "Moin"
    assert doc.source_type == "upload"


def test_optional_fields_default_to_none():
    """Optional fields should default to None."""
    doc = ExtractedDocument(
        text="Example",
        filename="example.txt",
    )

    assert doc.mime_type is None
    assert doc.page_count is None
    assert doc.title is None
    assert doc.author is None
    assert doc.source_type is None


def test_text_can_be_empty():
    """Empty text is allowed."""
    doc = ExtractedDocument(
        text="",
        filename="empty.txt",
    )

    assert doc.text == ""
    assert doc.filename == "empty.txt"