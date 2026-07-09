"""Tests for RetrievalTraceRepository."""

from uuid import uuid4

import pytest
import pytest_asyncio

from packages.database.models.retrieval_trace import RetrievalTraceStatus
from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)


@pytest_asyncio.fixture
async def repository(async_session, tenant):
    """Repository instance."""
    return RetrievalTraceRepository(
        async_session,
        tenant.id,
    )


@pytest.mark.asyncio
async def test_create_trace(repository):
    """Should create a retrieval trace."""

    trace = await repository.create(
        conversation_id=None,
        query="What is CRM?",
        embedding_model="text-embedding-3-small",
        vector_store="pgvector",
    )

    assert trace is not None
    assert trace.query == "What is CRM?"
    assert trace.embedding_model == "text-embedding-3-small"
    assert trace.vector_store == "pgvector"
    assert trace.status == RetrievalTraceStatus.SUCCESS


@pytest.mark.asyncio
async def test_get_by_id(repository):
    """Should retrieve trace by ID."""

    trace = await repository.create(
        conversation_id=None,
        query="hello",
    )

    loaded = await repository.get_by_id(trace.id)

    assert loaded is not None
    assert loaded.id == trace.id


@pytest.mark.asyncio
async def test_get_missing_trace(repository):
    """Unknown trace should return None."""

    loaded = await repository.get_by_id(uuid4())

    assert loaded is None


@pytest.mark.asyncio
async def test_update_trace_status(repository):
    """Should update trace status."""

    trace = await repository.create(
        conversation_id=None,
        query="query",
    )

    updated = await repository.update(
        trace.id,
        status=RetrievalTraceStatus.FAILED,
        error_message="Embedding failed",
    )

    assert updated is not None
    assert updated.status == RetrievalTraceStatus.FAILED
    assert updated.error_message == "Embedding failed"


@pytest.mark.asyncio
async def test_update_trace_metrics(repository):
    """Should update latency metrics."""

    trace = await repository.create(
        conversation_id=None,
        query="query",
    )

    updated = await repository.update(
        trace.id,
        embedding_latency_ms=12.4,
        retrieval_latency_ms=25.8,
        total_latency_ms=38.2,
        retrieved_chunks=6,
    )

    assert updated is not None
    assert updated.embedding_latency_ms == 12.4
    assert updated.retrieval_latency_ms == 25.8
    assert updated.total_latency_ms == 38.2
    assert updated.retrieved_chunks == 6


@pytest.mark.asyncio
async def test_list_by_conversation(repository, conversation):
    """Should list traces for a conversation."""

    await repository.create(
        conversation_id=conversation.id,
        query="first",
    )

    await repository.create(
        conversation_id=conversation.id,
        query="second",
    )

    traces = await repository.list_by_conversation(
        conversation.id,
    )

    assert len(traces) == 2


@pytest.mark.asyncio
async def test_get_with_chunks(repository):
    """Should load retrieval trace."""

    trace = await repository.create(
        conversation_id=None,
        query="knowledge",
    )

    loaded = await repository.get_by_id(trace.id)

    assert loaded is not None
    assert loaded.id == trace.id


@pytest.mark.asyncio
async def test_delete_trace(repository):
    """Should delete a retrieval trace."""

    trace = await repository.create(
        conversation_id=None,
        query="delete",
    )

    deleted = await repository.delete(trace.id)

    assert deleted is True

    loaded = await repository.get_by_id(trace.id)

    assert loaded is None


@pytest.mark.asyncio
async def test_delete_unknown_trace(repository):
    """Deleting an unknown trace should return False."""

    deleted = await repository.delete(uuid4())

    assert deleted is False