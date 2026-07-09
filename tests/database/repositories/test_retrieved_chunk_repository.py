"""Tests for RetrievedChunkRepository."""

from uuid import uuid4

import pytest

from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)


@pytest.fixture
async def repository(async_session, tenant):
    """Create repository instance."""
    return RetrievedChunkRepository(
        async_session,
        tenant.id,
    )


@pytest.mark.asyncio
async def test_create_chunk(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should create a retrieved chunk."""

    chunk = await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.96,
        chunk_preview="CRM Copilot is an AI-powered assistant.",
    )

    assert chunk is not None
    assert chunk.trace_id == retrieval_trace.id
    assert chunk.document_id == knowledge_document.id
    assert chunk.chunk_id == document_chunk.id
    assert chunk.rank == 1
    assert chunk.similarity_score == pytest.approx(0.96)
    assert (
        chunk.chunk_preview
        == "CRM Copilot is an AI-powered assistant."
    )


@pytest.mark.asyncio
async def test_get_by_id(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should retrieve a chunk by ID."""

    chunk = await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.91,
        chunk_preview="Example chunk",
    )

    loaded = await repository.get_by_id(chunk.id)

    assert loaded is not None
    assert loaded.id == chunk.id


@pytest.mark.asyncio
async def test_get_unknown_chunk(repository):
    """Unknown chunk should return None."""

    loaded = await repository.get_by_id(uuid4())

    assert loaded is None


@pytest.mark.asyncio
async def test_bulk_create(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should bulk-create retrieved chunks."""

    chunks = await repository.bulk_create(
        [
            {
                "trace_id": retrieval_trace.id,
                "document_id": knowledge_document.id,
                "chunk_id": document_chunk.id,
                "rank": 1,
                "similarity_score": 0.95,
                "chunk_preview": "Chunk One",
            },
            {
                "trace_id": retrieval_trace.id,
                "document_id": knowledge_document.id,
                "chunk_id": document_chunk.id,
                "rank": 2,
                "similarity_score": 0.87,
                "chunk_preview": "Chunk Two",
            },
        ]
    )

    assert len(chunks) == 2
    assert chunks[0].rank == 1
    assert chunks[1].rank == 2


@pytest.mark.asyncio
async def test_get_by_trace(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should return chunks ordered by rank."""

    await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=2,
        similarity_score=0.75,
        chunk_preview="Second",
    )

    await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.98,
        chunk_preview="First",
    )

    chunks = await repository.get_by_trace(
        retrieval_trace.id,
    )

    assert len(chunks) == 2
    assert chunks[0].rank == 1
    assert chunks[1].rank == 2


@pytest.mark.asyncio
async def test_delete_by_trace(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should delete all chunks for a trace."""

    await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.9,
        chunk_preview="Chunk A",
    )

    await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=2,
        similarity_score=0.8,
        chunk_preview="Chunk B",
    )

    deleted = await repository.delete_by_trace(
        retrieval_trace.id,
    )

    assert deleted == 2

    chunks = await repository.get_by_trace(
        retrieval_trace.id,
    )

    assert chunks == []


@pytest.mark.asyncio
async def test_delete_unknown_trace(repository):
    """Deleting chunks for an unknown trace should return zero."""

    deleted = await repository.delete_by_trace(
        uuid4(),
    )

    assert deleted == 0


@pytest.mark.asyncio
async def test_delete_chunk(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Should delete a single retrieved chunk."""

    chunk = await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.94,
        chunk_preview="Delete me",
    )

    deleted = await repository.delete(
        chunk.id,
    )

    assert deleted is True

    loaded = await repository.get_by_id(
        chunk.id,
    )

    assert loaded is None


@pytest.mark.asyncio
async def test_delete_unknown_chunk(repository):
    """Deleting an unknown chunk should return False."""

    deleted = await repository.delete(
        uuid4(),
    )

    assert deleted is False


@pytest.mark.asyncio
async def test_tenant_isolation(
    repository,
    retrieval_trace,
    knowledge_document,
    document_chunk,
):
    """Repository should enforce tenant isolation."""

    chunk = await repository.create(
        trace_id=retrieval_trace.id,
        document_id=knowledge_document.id,
        chunk_id=document_chunk.id,
        rank=1,
        similarity_score=0.92,
        chunk_preview="Tenant isolated chunk",
    )

    loaded = await repository.get_by_id(
        chunk.id,
    )

    assert loaded is not None
    assert loaded.tenant_id == repository.tenant_id