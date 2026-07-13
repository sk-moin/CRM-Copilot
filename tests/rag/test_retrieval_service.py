"""
tests/rag/test_retrieval_service.py
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.rag.retrieval_service import RetrievalService
from app.rag.retrievers.retriever import RetrievalResult
from packages.database.models.retrieval_trace import (
    RetrievalTraceStatus,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def retriever() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def retrieval_trace_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def retrieved_chunk_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
) -> RetrievalService:
    return RetrievalService(
        retriever=retriever,
        retrieval_trace_repository=retrieval_trace_repository,
        retrieved_chunk_repository=retrieved_chunk_repository,
    )


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def retrieval_trace():
    return SimpleNamespace(
        id=uuid4(),
    )


@pytest.fixture
def retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        documents=[
            Document(
                page_content="CRM overview",
                metadata={
                    "chunk_id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "title": "CRM Guide",
                },
            ),
            Document(
                page_content="Customer segmentation",
                metadata={
                    "chunk_id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "title": "Sales Playbook",
                },
            ),
        ],
        similarity_scores=[
            0.94,
            0.87,
        ],
    )

# --------------------------------------------------------------------------- #
# Successful Retrieval
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_success(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Successfully retrieve relevant chunks and persist observability data.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.return_value = retrieval_result

    result = await service.retrieve(
        conversation_id=conversation_id,
        query="What is CRM?",
        top_k=5,
        score_threshold=0.25,
    )

    # ------------------------------------------------------------------ #
    # Trace creation
    # ------------------------------------------------------------------ #

    retrieval_trace_repository.create.assert_awaited_once_with(
        conversation_id=conversation_id,
        query="What is CRM?",
    )

    # ------------------------------------------------------------------ #
    # Retriever invocation
    # ------------------------------------------------------------------ #

    retriever.retrieve.assert_awaited_once_with(
        query="What is CRM?",
        top_k=5,
        score_threshold=0.25,
        document_id=None,
    )

    # ------------------------------------------------------------------ #
    # Metrics
    # ------------------------------------------------------------------ #

    retrieval_trace_repository.update_metrics.assert_awaited_once()

    metrics_kwargs = (
        retrieval_trace_repository
        .update_metrics
        .await_args
        .kwargs
    )

    assert metrics_kwargs["retrieval_latency_ms"] >= 0

    assert metrics_kwargs["total_latency_ms"] >= 0

    assert (
        metrics_kwargs["retrieved_chunk"]
        == len(retrieval_result.documents)
    )

    # ------------------------------------------------------------------ #
    # Status
    # ------------------------------------------------------------------ #

    retrieval_trace_repository.update_status.assert_awaited_once_with(
        retrieval_trace.id,
        status=RetrievalTraceStatus.SUCCESS,
    )

    # ------------------------------------------------------------------ #
    # Retrieved chunks persisted
    # ------------------------------------------------------------------ #

    retrieved_chunk_repository.bulk_create.assert_awaited_once()

    payload = (
        retrieved_chunk_repository
        .bulk_create
        .await_args
        .args[0]
    )

    assert len(payload) == 2

    assert payload[0]["rank"] == 1
    assert payload[1]["rank"] == 2

    assert (
        payload[0]["similarity_score"]
        == retrieval_result.similarity_scores[0]
    )

    assert (
        payload[1]["similarity_score"]
        == retrieval_result.similarity_scores[1]
    )

    # ------------------------------------------------------------------ #
    # Returned object
    # ------------------------------------------------------------------ #

    assert result is retrieval_result

    assert len(result.documents) == 2

    assert result.similarity_scores == [0.94, 0.87]

# --------------------------------------------------------------------------- #
# Empty Retrieval & Retrieval Failure
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_with_no_results(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    conversation_id,
):
    """
    Retrieval should succeed even when no documents are found.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    empty_result = RetrievalResult(
        documents=[],
        similarity_scores=[],
    )

    retriever.retrieve.return_value = empty_result

    result = await service.retrieve(
        conversation_id=conversation_id,
        query="Unknown topic",
    )

    retrieval_trace_repository.update_status.assert_awaited_once_with(
        retrieval_trace.id,
        status=RetrievalTraceStatus.SUCCESS,
    )

    retrieval_trace_repository.update_metrics.assert_awaited_once()

    metrics = (
        retrieval_trace_repository
        .update_metrics
        .await_args
        .kwargs
    )

    assert metrics["retrieved_chunk"] == 0

    retrieved_chunk_repository.bulk_create.assert_not_awaited()

    assert result.documents == []

    assert result.similarity_scores == []


@pytest.mark.asyncio
async def test_retrieve_when_retriever_fails(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    conversation_id,
):
    """
    Any retriever exception should mark the trace as FAILED.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.side_effect = RuntimeError(
        "Vector search failed."
    )

    with pytest.raises(RuntimeError):
        await service.retrieve(
            conversation_id=conversation_id,
            query="CRM",
        )

    retrieval_trace_repository.update_metrics.assert_awaited_once()

    retrieval_trace_repository.update_status.assert_awaited_once()

    status_kwargs = (
        retrieval_trace_repository
        .update_status
        .await_args
        .kwargs
    )

    assert (
        status_kwargs["status"]
        == RetrievalTraceStatus.FAILED
    )

    assert (
        status_kwargs["error_message"]
        == "Vector search failed."
    )

    retrieved_chunk_repository.bulk_create.assert_not_awaited()

# --------------------------------------------------------------------------- #
# Repository Failure & Payload Validation
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_when_chunk_repository_fails(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    If persisting retrieved chunks fails, the retrieval trace should be
    marked as FAILED and the exception should be propagated.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.return_value = retrieval_result

    retrieved_chunk_repository.bulk_create.side_effect = RuntimeError(
        "Failed to persist retrieved chunks."
    )

    with pytest.raises(RuntimeError):
        await service.retrieve(
            conversation_id=conversation_id,
            query="CRM",
        )

    retrieval_trace_repository.update_metrics.assert_awaited()

    retrieval_trace_repository.update_status.assert_awaited()

    kwargs = (
        retrieval_trace_repository
        .update_status
        .await_args
        .kwargs
    )

    assert (
        kwargs["status"]
        == RetrievalTraceStatus.FAILED
    )

    assert (
        kwargs["error_message"]
        == "Failed to persist retrieved chunks."
    )


@pytest.mark.asyncio
async def test_retrieved_chunk_payload_is_correct(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Verify that RetrievedChunkRepository receives the expected payload.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.return_value = retrieval_result

    await service.retrieve(
        conversation_id=conversation_id,
        query="CRM",
    )

    payload = (
        retrieved_chunk_repository
        .bulk_create
        .await_args
        .args[0]
    )

    assert len(payload) == len(
        retrieval_result.documents,
    )

    for index, row in enumerate(payload):

        assert (
            row["retrieval_trace_id"]
            == retrieval_trace.id
        )

        assert row["rank"] == index + 1

        assert (
            row["similarity_score"]
            == retrieval_result.similarity_scores[index]
        )

        assert (
            row["document_chunk_id"]
            == retrieval_result.documents[index]
            .metadata["chunk_id"]
            or str(row["document_chunk_id"])
            == retrieval_result.documents[index]
            .metadata["chunk_id"]
        )


@pytest.mark.asyncio
async def test_metrics_are_recorded(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Ensure retrieval latency metrics are always recorded.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.return_value = retrieval_result

    await service.retrieve(
        conversation_id=conversation_id,
        query="CRM metrics",
    )

    retrieval_trace_repository.update_metrics.assert_awaited_once()

    metrics = (
        retrieval_trace_repository
        .update_metrics
        .await_args
        .kwargs
    )

    assert metrics["retrieval_latency_ms"] >= 0

    assert metrics["total_latency_ms"] >= 0

    assert (
        metrics["retrieved_chunk"]
        == len(retrieval_result.documents)
    )


@pytest.mark.asyncio
async def test_retrieve_preserves_similarity_scores(
    service: RetrievalService,
    retriever: AsyncMock,
    retrieval_trace_repository: AsyncMock,
    retrieved_chunk_repository: AsyncMock,
    retrieval_trace,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Returned RetrievalResult should not be modified by RetrievalService.
    """

    retrieval_trace_repository.create.return_value = retrieval_trace

    retriever.retrieve.return_value = retrieval_result

    result = await service.retrieve(
        conversation_id=conversation_id,
        query="CRM",
    )

    assert result is retrieval_result

    assert result.documents == retrieval_result.documents

    assert (
        result.similarity_scores
        == retrieval_result.similarity_scores
    )