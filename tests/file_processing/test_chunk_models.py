"""Tests for text chunk models."""

from app.file_processing.chunkers.models import TextChunk


def test_create_text_chunk():
    """Create a TextChunk with all fields."""
    chunk = TextChunk(
        text="This is a test chunk.",
        chunk_index=0,
        start_char=0,
        end_char=21,
        token_count=5,
        metadata={
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
    )

    assert chunk.text == "This is a test chunk."
    assert chunk.chunk_index == 0
    assert chunk.start_char == 0
    assert chunk.end_char == 21
    assert chunk.token_count == 5
    assert chunk.metadata["chunk_size"] == 1000
    assert chunk.metadata["chunk_overlap"] == 200


def test_metadata_defaults_to_empty_dict():
    """Metadata should default to an empty dictionary."""
    chunk = TextChunk(
        text="Hello",
        chunk_index=1,
        start_char=0,
        end_char=5,
        token_count=1,
    )

    assert chunk.metadata == {}


def test_chunk_positions_are_preserved():
    """Character positions should be stored correctly."""
    chunk = TextChunk(
        text="abcdef",
        chunk_index=2,
        start_char=10,
        end_char=16,
        token_count=2,
    )

    assert chunk.start_char == 10
    assert chunk.end_char == 16
    assert chunk.end_char - chunk.start_char == 6