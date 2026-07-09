"""Tests for RetrievedChunk model."""

from uuid import uuid4

from packages.database.models.retrieved_chunk import RetrievedChunk


def test_create_retrieved_chunk():
    """Test RetrievedChunk creation."""

    chunk = RetrievedChunk(
        tenant_id=uuid4(),
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=1,
        similarity_score=0.93,
        chunk_preview="This is a chunk preview.",
    )

    assert chunk.rank == 1
    assert chunk.similarity_score == 0.93
    assert chunk.chunk_preview == "This is a chunk preview."


def test_chunk_metadata():
    """Test metadata."""

    metadata = {
        "page": 2,
        "section": "Introduction",
    }

    chunk = RetrievedChunk(
        tenant_id=uuid4(),
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=2,
        similarity_score=0.88,
        chunk_preview="Preview",
        retrieval_metadata=metadata,
    )

    assert chunk.retrieval_metadata == metadata


def test_chunk_rank():
    """Test rank assignment."""

    chunk = RetrievedChunk(
        tenant_id=uuid4(),
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=5,
        similarity_score=0.81,
        chunk_preview="Ranked chunk",
    )

    assert chunk.rank == 5


def test_chunk_similarity_score():
    """Test similarity score."""

    chunk = RetrievedChunk(
        tenant_id=uuid4(),
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=1,
        similarity_score=1.0,
        chunk_preview="Perfect match",
    )

    assert chunk.similarity_score == 1.0


def test_chunk_relationship_fields():
    """Relationship attributes exist."""

    chunk = RetrievedChunk(
        tenant_id=uuid4(),
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=1,
        similarity_score=0.95,
        chunk_preview="Relationship",
    )

    assert chunk.trace is None
    assert chunk.document is None
    assert chunk.chunk is None