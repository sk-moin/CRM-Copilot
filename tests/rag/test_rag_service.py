"""
tests/rag/test_rag_service.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.rag.chains.rag_chain import RAGResponse
from app.rag.exceptions import (
    RAGGenerationError,
    RetrievalError,
)
from app.rag.rag_service import RAGService
from app.rag.retrievers.retriever import RetrievalResult


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def retrieval_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def rag_chain():
    """
    generate() is async -> AsyncMock

    stream() is an async generator -> regular Mock returning
    an async generator.
    """
    chain = Mock()

    chain.generate = AsyncMock()
    chain.stream = Mock()

    return chain


@pytest.fixture
def service(
    retrieval_service: AsyncMock,
    rag_chain: Mock,
) -> RAGService:
    return RAGService(
        retrieval_service=retrieval_service,
        rag_chain=rag_chain,
    )


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        documents=[
            Document(
                page_content="CRM overview",
                metadata={
                    "chunk_id": str(uuid4()),
                    "title": "CRM Guide",
                },
            ),
            Document(
                page_content="Sales pipeline",
                metadata={
                    "chunk_id": str(uuid4()),
                    "title": "Sales Playbook",
                },
            ),
        ],
        similarity_scores=[
            0.95,
            0.91,
        ],
    )


@pytest.fixture
def rag_response(
    retrieval_result: RetrievalResult,
) -> RAGResponse:
    return RAGResponse(
        answer="CRM helps manage customer relationships.",
        documents=retrieval_result.documents,
        similarity_scores=retrieval_result.similarity_scores,
    )

# --------------------------------------------------------------------------- #
# ask()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_ask_success(
    service: RAGService,
    retrieval_service: AsyncMock,
    rag_chain: Mock,
    retrieval_result: RetrievalResult,
    rag_response: RAGResponse,
    conversation_id,
):
    """
    ask() should retrieve documents and generate an answer.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    rag_chain.generate.return_value = rag_response

    result = await service.ask(
        conversation_id=conversation_id,
        query="What is CRM?",
        top_k=5,
        score_threshold=0.25,
    )

    retrieval_service.retrieve.assert_awaited_once_with(
        conversation_id=conversation_id,
        query="What is CRM?",
        top_k=5,
        score_threshold=0.25,
        document_id=None,
    )

    rag_chain.generate.assert_awaited_once_with(
        query="What is CRM?",
        retrieval_result=retrieval_result,
    )

    assert result is rag_response


@pytest.mark.asyncio
async def test_ask_wraps_generation_error(
    service: RAGService,
    retrieval_service: AsyncMock,
    rag_chain: Mock,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Generation failures should be wrapped as RAGGenerationError.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    rag_chain.generate.side_effect = RuntimeError(
        "LLM failure",
    )

    with pytest.raises(RAGGenerationError):
        await service.ask(
            conversation_id=conversation_id,
            query="CRM",
        )


@pytest.mark.asyncio
async def test_ask_wraps_retrieval_error(
    service: RAGService,
    retrieval_service: AsyncMock,
    conversation_id,
):
    """
    Retrieval failures should also surface as RAGGenerationError.
    """

    retrieval_service.retrieve.side_effect = RetrievalError(
        "Vector search failed.",
    )

    with pytest.raises(RAGGenerationError):
        await service.ask(
            conversation_id=conversation_id,
            query="CRM",
        )

# --------------------------------------------------------------------------- #
# retrieve()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_success(
    service: RAGService,
    retrieval_service: AsyncMock,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    retrieve() should delegate directly to RetrievalService.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    result = await service.retrieve(
        conversation_id=conversation_id,
        query="CRM",
        top_k=10,
        score_threshold=0.30,
        document_id=None,
    )

    retrieval_service.retrieve.assert_awaited_once_with(
        conversation_id=conversation_id,
        query="CRM",
        top_k=10,
        score_threshold=0.30,
        document_id=None,
    )

    assert result is retrieval_result


@pytest.mark.asyncio
async def test_retrieve_wraps_retrieval_error(
    service: RAGService,
    retrieval_service: AsyncMock,
    conversation_id,
):
    """
    Retrieval failures should be wrapped as RetrievalError.
    """

    retrieval_service.retrieve.side_effect = RuntimeError(
        "Database unavailable.",
    )

    with pytest.raises(RetrievalError):
        await service.retrieve(
            conversation_id=conversation_id,
            query="CRM",
        )


# --------------------------------------------------------------------------- #
# stream()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_stream_success(
    service: RAGService,
    retrieval_service: AsyncMock,
    rag_chain: Mock,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    stream() should retrieve documents and delegate streaming to RAGChain.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    async def fake_stream():
        for token in [
            "CRM ",
            "helps ",
            "businesses.",
        ]:
            yield token

    rag_chain.stream.return_value = fake_stream()

    tokens = []

    async for token in service.stream(
        conversation_id=conversation_id,
        query="CRM",
    ):
        tokens.append(token)

    retrieval_service.retrieve.assert_awaited_once()

    rag_chain.stream.assert_called_once_with(
        query="CRM",
        retrieval_result=retrieval_result,
    )

    assert "".join(tokens) == "CRM helps businesses."

@pytest.mark.asyncio
async def test_stream_wraps_generation_error(
    service: RAGService,
    retrieval_service: AsyncMock,
    rag_chain: Mock,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Exceptions raised while streaming should be wrapped as
    RAGGenerationError.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    async def failing_stream():
        raise RuntimeError("Streaming failed.")
        yield  # pragma: no cover

    rag_chain.stream.return_value = failing_stream()

    with pytest.raises(RAGGenerationError):
        async for _ in service.stream(
            conversation_id=conversation_id,
            query="CRM",
        ):
            pass


@pytest.mark.asyncio
async def test_stream_wraps_retrieval_error(
    service: RAGService,
    retrieval_service: AsyncMock,
    conversation_id,
):
    """
    Retrieval failures before streaming should be wrapped as
    RAGGenerationError.
    """

    retrieval_service.retrieve.side_effect = RetrievalError(
        "Vector search failed.",
    )

    with pytest.raises(RAGGenerationError):
        async for _ in service.stream(
            conversation_id=conversation_id,
            query="CRM",
        ):
            pass


@pytest.mark.asyncio
async def test_stream_forwards_parameters(
    service: RAGService,
    retrieval_service: AsyncMock,
    rag_chain: Mock,
    retrieval_result: RetrievalResult,
    conversation_id,
):
    """
    Verify that all parameters are forwarded correctly.
    """

    retrieval_service.retrieve.return_value = retrieval_result

    async def fake_stream():
        yield "answer"

    rag_chain.stream.return_value = fake_stream()

    async for _ in service.stream(
        conversation_id=conversation_id,
        query="Explain CRM",
        top_k=8,
        score_threshold=0.45,
        document_id=uuid4(),
    ):
        pass

    kwargs = retrieval_service.retrieve.await_args.kwargs

    assert kwargs["conversation_id"] == conversation_id
    assert kwargs["query"] == "Explain CRM"
    assert kwargs["top_k"] == 8
    assert kwargs["score_threshold"] == 0.45
    assert kwargs["document_id"] is not None