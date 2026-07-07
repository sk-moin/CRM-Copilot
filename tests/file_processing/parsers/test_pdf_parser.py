"""Tests for PDFParser."""

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from app.file_processing.models.extracted_document import ExtractedDocument
from app.file_processing.parsers.pdf_parser import PDFParser


def test_can_parse_pdf():
    """Parser should recognize .pdf files."""
    assert PDFParser.can_parse("sample.pdf")
    assert PDFParser.can_parse(Path("sample.PDF"))


def test_cannot_parse_other_extensions():
    """Parser should reject unsupported extensions."""
    assert not PDFParser.can_parse("sample.txt")
    assert not PDFParser.can_parse("sample.docx")


def test_parse_pdf_file(tmp_path):
    """Parse a simple PDF document."""
    file_path = tmp_path / "sample.pdf"

    pdf = canvas.Canvas(str(file_path))
    pdf.drawString(100, 750, "Hello PDF")
    pdf.drawString(100, 730, "Second line")
    pdf.save()

    extracted = PDFParser.parse(file_path)

    assert isinstance(extracted, ExtractedDocument)
    assert extracted.filename == "sample.pdf"
    assert "Hello PDF" in extracted.text
    assert "Second line" in extracted.text
    assert extracted.page_count == 1


def test_parse_empty_pdf(tmp_path):
    """Empty PDF should still parse successfully."""
    file_path = tmp_path / "empty.pdf"

    pdf = canvas.Canvas(str(file_path))
    pdf.save()

    extracted = PDFParser.parse(file_path)

    assert extracted.filename == "empty.pdf"
    assert extracted.text == ""
    assert extracted.page_count == 1


def test_parse_unicode_pdf(tmp_path):
    """Unicode text should not cause parser failure."""
    file_path = tmp_path / "unicode.pdf"

    pdf = canvas.Canvas(str(file_path))
    pdf.drawString(100, 750, "Hello World")
    pdf.save()

    extracted = PDFParser.parse(file_path)

    assert "Hello World" in extracted.text


def test_missing_pdf_file():
    """Missing file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        PDFParser.parse("missing.pdf")


def test_corrupt_pdf_file(tmp_path):
    """Corrupt PDF should raise an exception."""
    file_path = tmp_path / "corrupt.pdf"

    file_path.write_bytes(b"This is not a valid PDF")

    with pytest.raises(Exception):
        PDFParser.parse(file_path)


def test_multi_page_pdf(tmp_path):
    """Parser should extract text from multiple pages."""
    file_path = tmp_path / "multi.pdf"

    pdf = canvas.Canvas(str(file_path))
    pdf.drawString(100, 750, "Page One")
    pdf.showPage()
    pdf.drawString(100, 750, "Page Two")
    pdf.save()

    extracted = PDFParser.parse(file_path)

    assert "Page One" in extracted.text
    assert "Page Two" in extracted.text
    assert extracted.page_count == 2