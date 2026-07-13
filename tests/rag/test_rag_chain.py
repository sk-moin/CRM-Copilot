"""
tests/rag/test_rag_chain.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.rag.chains.rag_chain import (
    RAGChain,
    RAGResponse,
    build_rag_chain,
)
from app.rag.exceptions import RAGGenerationError
from app.rag.retrievers.retriever import RetrievalResult


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def provider():
    provider = Mock()

    provider.complete = AsyncMock()

    return provider


@pytest.fixture
def rag_chain(
    provider: AsyncMock,
) -> RAGChain:
    """
    Chain under test.
    """
    return RAGChain(
        provider=provider,
    )


@pytest.fixture
def documents() -> list[Document]:
    """
    Example retrieved documents.
    """
    return [
        Document(
            page_content=(
                "CRM stands for Customer Relationship "
                "Management."
            ),
            metadata={
                "title": "CRM Guide",
                "document_id": str(uuid4()),
            },
        ),
        Document(
            page_content=(
                "Sales opportunities are tracked "
                "using pipelines."
            ),
            metadata={
                "filename": "sales.pdf",
                "document_id": str(uuid4()),
            },
        ),
    ]


@pytest.fixture
def retrieval_result(
    documents: list[Document],
) -> RetrievalResult:
    """
    Example RetrievalResult.
    """
    return RetrievalResult(
        documents=documents,
        similarity_scores=[
            0.96,
            0.91,
        ],
    )


# --------------------------------------------------------------------------- #
# generate()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_success(
    rag_chain: RAGChain,
    provider: AsyncMock,
    retrieval_result: RetrievalResult,
):
    """
    Successful generation should return a RAGResponse.
    """

    provider.complete.return_value = (
        "CRM helps manage customer relationships."
    )

    response = await rag_chain.generate(
        query="What is CRM?",
        retrieval_result=retrieval_result,
    )

    assert isinstance(
        response,
        RAGResponse,
    )

    assert (
        response.answer
        == "CRM helps manage customer relationships."
    )

    assert (
        response.documents
        == retrieval_result.documents
    )

    assert (
        response.similarity_scores
        == retrieval_result.similarity_scores
    )

    provider.complete.assert_awaited_once()

    messages = (
        provider.complete.await_args.kwargs["messages"]
    )

    assert len(messages) == 2

    assert messages[0]["role"] == "system"

    assert messages[1]["role"] == "user"

    assert "What is CRM?" in messages[1]["content"]

    assert "CRM Guide" in messages[1]["content"]


@pytest.mark.asyncio
async def test_generate_rejects_empty_query(
    rag_chain: RAGChain,
    retrieval_result: RetrievalResult,
):
    """
    Empty queries should be rejected.
    """

    with pytest.raises(
        RAGGenerationError,
    ):
        await rag_chain.generate(
            query="",
            retrieval_result=retrieval_result,
        )


@pytest.mark.asyncio
async def test_generate_rejects_whitespace_query(
    rag_chain: RAGChain,
    retrieval_result: RetrievalResult,
):
    """
    Whitespace-only queries should be rejected.
    """

    with pytest.raises(
        RAGGenerationError,
    ):
        await rag_chain.generate(
            query="     ",
            retrieval_result=retrieval_result,
        )


@pytest.mark.asyncio
async def test_generate_when_provider_fails(
    rag_chain: RAGChain,
    provider: AsyncMock,
    retrieval_result: RetrievalResult,
):
    """
    Provider failures should become
    RAGGenerationError.
    """

    provider.complete.side_effect = RuntimeError(
        "LLM unavailable"
    )

    with pytest.raises(
        RAGGenerationError,
    ):
        await rag_chain.generate(
            query="CRM",
            retrieval_result=retrieval_result,
        )

# --------------------------------------------------------------------------- #
# stream()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_stream_success(
    rag_chain: RAGChain,
    provider: AsyncMock,
    retrieval_result: RetrievalResult,
):
    """
    Streamed tokens should be yielded in order.
    """

    async def fake_stream(*, messages):
        assert len(messages) == 2

        yield "CRM "
        yield "helps "
        yield "businesses."

    provider.stream = Mock(side_effect=fake_stream)

    chunks = []

    async for chunk in rag_chain.stream(
        query="What is CRM?",
        retrieval_result=retrieval_result,
    ):
        chunks.append(chunk)

    assert chunks == [
        "CRM ",
        "helps ",
        "businesses.",
    ]

    provider.stream.assert_called_once()


@pytest.mark.asyncio
async def test_stream_rejects_empty_query(
    rag_chain: RAGChain,
    retrieval_result: RetrievalResult,
):
    """
    Empty queries should raise an error.
    """

    with pytest.raises(
        RAGGenerationError,
    ):
        async for _ in rag_chain.stream(
            query="",
            retrieval_result=retrieval_result,
        ):
            pass


@pytest.mark.asyncio
async def test_stream_rejects_whitespace_query(
    rag_chain: RAGChain,
    retrieval_result: RetrievalResult,
):
    """
    Whitespace-only queries should raise an error.
    """

    with pytest.raises(
        RAGGenerationError,
    ):
        async for _ in rag_chain.stream(
            query="     ",
            retrieval_result=retrieval_result,
        ):
            pass


@pytest.mark.asyncio
async def test_stream_when_provider_fails(
    rag_chain: RAGChain,
    provider: AsyncMock,
    retrieval_result: RetrievalResult,
):
    """
    Exceptions from the provider should propagate.
    """

    async def failing_stream(*, messages):
        raise RuntimeError("Streaming failed.")
        yield  # pragma: no cover

    provider.stream = failing_stream

    with pytest.raises(
        RuntimeError,
    ):
        async for _ in rag_chain.stream(
            query="CRM",
            retrieval_result=retrieval_result,
        ):
            pass


@pytest.mark.asyncio
async def test_stream_builds_context_correctly(
    rag_chain: RAGChain,
    provider: AsyncMock,
    retrieval_result: RetrievalResult,
):
    """
    Context should be included in the prompt.
    """

    async def fake_stream(*, messages):
        user_prompt = messages[1]["content"]

        assert "CRM Guide" in user_prompt
        assert "Sales opportunities" in user_prompt
        assert "Question:" in user_prompt

        yield "OK"

    provider.stream = fake_stream

    chunks = []

    async for chunk in rag_chain.stream(
        query="Explain CRM",
        retrieval_result=retrieval_result,
    ):
        chunks.append(chunk)

    assert chunks == ["OK"]

# --------------------------------------------------------------------------- #
# _build_context()
# --------------------------------------------------------------------------- #


def test_build_context_with_documents(
    rag_chain: RAGChain,
    documents: list[Document],
):
    """
    Context should include titles and page content.
    """

    context = rag_chain._build_context(
        documents,
    )

    assert "[1] CRM Guide" in context

    assert (
        "CRM stands for Customer Relationship Management."
        in context
    )

    assert "[2] sales.pdf" in context

    assert (
        "Sales opportunities are tracked using pipelines."
        in context
    )


def test_build_context_without_documents(
    rag_chain: RAGChain,
):
    """
    Empty retrieval results should return the fallback message.
    """

    context = rag_chain._build_context([])

    assert (
        context
        == "No relevant context found."
    )


def test_build_context_without_metadata(
    rag_chain: RAGChain,
):
    """
    Documents without metadata should receive default titles.
    """

    docs = [
        Document(
            page_content="First document",
            metadata={},
        ),
        Document(
            page_content="Second document",
            metadata={},
        ),
    ]

    context = rag_chain._build_context(
        docs,
    )

    assert "[1] Document 1" in context

    assert "[2] Document 2" in context

    assert "First document" in context

    assert "Second document" in context


def test_build_context_prefers_title_over_filename(
    rag_chain: RAGChain,
):
    """
    Title should take precedence over filename.
    """

    docs = [
        Document(
            page_content="Example",
            metadata={
                "title": "CRM Handbook",
                "filename": "crm.pdf",
            },
        ),
    ]

    context = rag_chain._build_context(
        docs,
    )

    assert "[1] CRM Handbook" in context

    assert "crm.pdf" not in context


# --------------------------------------------------------------------------- #
# RAGResponse
# --------------------------------------------------------------------------- #


def test_rag_response_dataclass(
    documents: list[Document],
):
    """
    RAGResponse should expose all fields.
    """

    response = RAGResponse(
        answer="Example answer",
        documents=documents,
        similarity_scores=[
            0.96,
            0.91,
        ],
    )

    assert (
        response.answer
        == "Example answer"
    )

    assert (
        response.documents
        == documents
    )

    assert (
        response.similarity_scores
        == [0.96, 0.91]
    )


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def test_build_rag_chain(
    provider: AsyncMock,
):
    """
    Factory should return a configured RAGChain.
    """

    chain = build_rag_chain(
        provider=provider,
    )

    assert isinstance(
        chain,
        RAGChain,
    )

    assert chain.provider is provider