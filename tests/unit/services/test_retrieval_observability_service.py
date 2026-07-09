"""Unit tests for retrieval observability services."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.retrieval_trace_service import RetrievalTraceService
from app.services.retrieved_chunk_service import RetrievedChunkService


@pytest.fixture
def trace_repository():
    return AsyncMock()


@pytest.fixture
def chunk_repository():
    return AsyncMock()


@pytest.fixture
def trace_service(trace_repository):
    return RetrievalTraceService(trace_repository)


@pytest.fixture
def chunk_service(chunk_repository):
    return RetrievedChunkService(chunk_repository)


# ----------------------------------------------------------------------
# RetrievalTraceService
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_trace(trace_service, trace_repository):
    """Should create a retrieval trace."""

    trace = SimpleNamespace(id=uuid4())

    trace_repository.create.return_value = trace

    result = await trace_service.create_trace(
        query="What is RAG?",
        conversation_id=uuid4(),
    )

    assert result is trace
    trace_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trace(trace_service, trace_repository):
    """Should fetch trace by id."""

    trace = SimpleNamespace(id=uuid4())

    trace_repository.get_by_id.return_value = trace

    result = await trace_service.get_trace(trace.id)

    assert result is trace

    trace_repository.get_by_id.assert_awaited_once_with(trace.id)


@pytest.mark.asyncio
async def test_list_by_conversation(
    trace_service,
    trace_repository,
):
    """Should return conversation traces."""

    conversation_id = uuid4()

    traces = [
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(id=uuid4()),
    ]

    trace_repository.list_by_conversation.return_value = traces

    result = await trace_service.list_by_conversation(conversation_id)

    assert result == traces

    trace_repository.list_by_conversation.assert_awaited_once_with(
        conversation_id,
        limit=100,
        offset=0,
    )


@pytest.mark.asyncio
async def test_update_trace(trace_service, trace_repository):
    """Should update trace."""

    trace = SimpleNamespace(id=uuid4())

    trace_repository.update.return_value = trace

    result = await trace_service.update_trace(
        trace.id,
        status="success",
    )

    assert result is trace

    trace_repository.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_trace(trace_service, trace_repository):
    """Should delete trace."""

    trace_repository.delete.return_value = True

    result = await trace_service.delete_trace(uuid4())

    assert result is True

    trace_repository.delete.assert_awaited_once()


# ----------------------------------------------------------------------
# RetrievedChunkService
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_chunk(chunk_service, chunk_repository):
    """Should create retrieved chunk."""

    chunk = SimpleNamespace(id=uuid4())

    chunk_repository.create.return_value = chunk

    result = await chunk_service.create_chunk(
        trace_id=uuid4(),
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=1,
        similarity_score=0.92,
        chunk_preview="Example",
    )

    assert result is chunk

    chunk_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_create_chunks(
    chunk_service,
    chunk_repository,
):
    """Should bulk create chunks."""

    created = [
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(id=uuid4()),
    ]

    chunk_repository.bulk_create.return_value = created

    payload = [
        {
            "trace_id": uuid4(),
            "document_id": uuid4(),
            "chunk_id": uuid4(),
            "rank": 1,
            "similarity_score": 0.91,
            "chunk_preview": "Chunk 1",
        },
        {
            "trace_id": uuid4(),
            "document_id": uuid4(),
            "chunk_id": uuid4(),
            "rank": 2,
            "similarity_score": 0.87,
            "chunk_preview": "Chunk 2",
        },
    ]

    result = await chunk_service.bulk_create(payload)

    assert result == created

    chunk_repository.bulk_create.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_get_by_trace(
    chunk_service,
    chunk_repository,
):
    """Should return chunks for a trace."""

    trace_id = uuid4()

    chunks = [
        SimpleNamespace(rank=1),
        SimpleNamespace(rank=2),
    ]

    chunk_repository.get_by_trace.return_value = chunks

    result = await chunk_service.get_by_trace(trace_id)

    assert result == chunks

    chunk_repository.get_by_trace.assert_awaited_once_with(trace_id)


@pytest.mark.asyncio
async def test_delete_by_trace(
    chunk_service,
    chunk_repository,
):
    """Should delete chunks for a trace."""

    trace_id = uuid4()

    chunk_repository.delete_by_trace.return_value = 3

    deleted = await chunk_service.delete_by_trace(trace_id)

    assert deleted == 3

    chunk_repository.delete_by_trace.assert_awaited_once_with(trace_id)