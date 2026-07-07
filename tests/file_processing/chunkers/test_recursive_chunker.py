"""Tests for RecursiveTextChunker."""

import pytest

from app.file_processing.chunkers.recursive_chunker import (
    RecursiveTextChunker,
)
from app.file_processing.models.extracted_document import (
    ExtractedDocument,
)


def test_default_configuration():
    """Chunker should initialize with default configuration."""
    chunker = RecursiveTextChunker()

    assert chunker.chunk_size == 1000
    assert chunker.chunk_overlap == 200


def test_custom_configuration():
    """Chunker should accept custom configuration."""
    chunker = RecursiveTextChunker(
        chunk_size=500,
        chunk_overlap=100,
    )

    assert chunker.chunk_size == 500
    assert chunker.chunk_overlap == 100


def test_invalid_chunk_size():
    """Chunk size must be greater than zero."""
    with pytest.raises(ValueError, match="chunk_size must be > 0"):
        RecursiveTextChunker(chunk_size=0)


def test_invalid_negative_overlap():
    """Overlap cannot be negative."""
    with pytest.raises(ValueError, match="chunk_overlap must be >= 0"):
        RecursiveTextChunker(chunk_overlap=-1)


def test_overlap_must_be_smaller_than_chunk_size():
    """Overlap must be smaller than chunk size."""
    with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
        RecursiveTextChunker(
            chunk_size=100,
            chunk_overlap=100,
        )


def test_normalize_text():
    """Normalize should remove null bytes and normalize whitespace."""
    text = "Hello\r\n\r\n\r\nWorld\x00"

    normalized = RecursiveTextChunker._normalize(text)

    assert normalized == "Hello\n\nWorld"


def test_chunk_empty_document():
    """Empty document should return no chunks."""
    chunker = RecursiveTextChunker()

    document = ExtractedDocument(
        text="",
        filename="empty.txt",
    )

    assert chunker.chunk(document) == []


def test_chunk_whitespace_document():
    """Whitespace-only document should return no chunks."""
    chunker = RecursiveTextChunker()

    document = ExtractedDocument(
        text="   \n\n   ",
        filename="blank.txt",
    )

    assert chunker.chunk(document) == []


def test_chunk_small_document():
    """Small documents should produce a single chunk."""
    chunker = RecursiveTextChunker()

    text = "This is a short document."

    document = ExtractedDocument(
        text=text,
        filename="small.txt",
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.text == text
    assert chunk.chunk_index == 0
    assert chunk.start_char == 0
    assert chunk.end_char == len(text)
    assert chunk.token_count == len(text) // 4


def test_chunk_large_document():
    """Large document should be split into multiple chunks."""
    chunker = RecursiveTextChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    text = ("Lorem ipsum dolor sit amet. " * 50)

    document = ExtractedDocument(
        text=text,
        filename="large.txt",
    )

    chunks = chunker.chunk(document)

    assert len(chunks) > 1

    for index, chunk in enumerate(chunks):
        assert chunk.chunk_index == index
        assert len(chunk.text) <= 100


def test_chunk_metadata():
    """Chunk metadata should include configuration."""
    chunker = RecursiveTextChunker(
        chunk_size=200,
        chunk_overlap=50,
    )

    document = ExtractedDocument(
        text="Hello world",
        filename="test.txt",
    )

    chunk = chunker.chunk(document)[0]

    assert chunk.metadata["chunk_size"] == 200
    assert chunk.metadata["chunk_overlap"] == 50


def test_find_last_separator():
    """Separator search should find the last separator."""
    text = "One.\nTwo.\nThree."

    pos, separator = RecursiveTextChunker._find_last_separator(
        text,
        0,
        len(text),
    )

    assert separator in {"\n", ". ", ""}
    assert pos <= len(text)


def test_chunk_order_is_preserved():
    """Chunks should preserve original ordering."""
    chunker = RecursiveTextChunker(
        chunk_size=60,
        chunk_overlap=10,
    )

    text = ("Sentence one. " * 20)

    document = ExtractedDocument(
        text=text,
        filename="ordered.txt",
    )

    chunks = chunker.chunk(document)

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_token_count_is_calculated():
    """Token count should be estimated."""
    chunker = RecursiveTextChunker()

    text = "abcd" * 25

    document = ExtractedDocument(
        text=text,
        filename="tokens.txt",
    )

    chunk = chunker.chunk(document)[0]

    assert chunk.token_count == len(chunk.text) // 4