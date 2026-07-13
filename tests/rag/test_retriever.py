"""
tests/rag/test_retriever.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.rag.retrievers.retriever import (
    RetrievalResult,
    Retriever,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def vector_store() -> AsyncMock:
    """
    Mock PGVectorStore.
    """
    return AsyncMock()


@pytest.fixture
def retriever(
    vector_store: AsyncMock,
) -> Retriever:
    """
    Retriever under test.
    """
    return Retriever(
        vector_store=vector_store,
    )


@pytest.fixture
def search_results():
    """
    Example vector search results.
    """
    return [
        (
            Document(
                page_content="CRM stands for Customer Relationship Management.",
                metadata={
                    "chunk_id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "title": "CRM Guide",
                },
            ),
            0.96,
        ),
        (
            Document(
                page_content="Sales opportunities are tracked in pipelines.",
                metadata={
                    "chunk_id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "title": "Sales Playbook",
                },
            ),
            0.91,
        ),
    ]

# --------------------------------------------------------------------------- #
# retrieve()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_success(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Retriever should return RetrievalResult from the vector store.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="What is CRM?",
        top_k=5,
        score_threshold=0.25,
        document_id=None,
    )

    vector_store.similarity_search_with_scores.assert_awaited_once_with(
        query="What is CRM?",
        k=5,
        document_id=None,
    )

    assert isinstance(result, RetrievalResult)

    assert len(result.documents) == 2

    assert result.documents[0] == search_results[0][0]

    assert result.documents[1] == search_results[1][0]

    assert result.similarity_scores == [
        0.96,
        0.91,
    ]

    assert result.retrieved_chunks == 2


@pytest.mark.asyncio
async def test_retrieve_with_document_filter(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    document_id should be forwarded to the vector store.
    """

    document_id = uuid4()

    vector_store.similarity_search_with_scores.return_value = search_results

    await retriever.retrieve(
        query="CRM",
        top_k=3,
        score_threshold=0.5,
        document_id=document_id,
    )

    vector_store.similarity_search_with_scores.assert_awaited_once_with(
        query="CRM",
        k=3,
        document_id=document_id,
    )


@pytest.mark.asyncio
async def test_retrieve_empty_results(
    retriever: Retriever,
    vector_store: AsyncMock,
):
    """
    Empty vector search should produce an empty RetrievalResult.
    """

    vector_store.similarity_search_with_scores.return_value = []

    result = await retriever.retrieve(
        query="Unknown query",
    )

    assert result.documents == []

    assert result.similarity_scores == []

    assert result.retrieved_chunks == 0

# --------------------------------------------------------------------------- #
# Error Handling
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_when_vector_store_raises(
    retriever: Retriever,
    vector_store: AsyncMock,
):
    """
    Exceptions from the vector store should propagate.
    """

    vector_store.similarity_search_with_scores.side_effect = RuntimeError(
        "Vector search failed.",
    )

    with pytest.raises(RuntimeError):
        await retriever.retrieve(
            query="CRM",
        )


@pytest.mark.asyncio
async def test_retrieve_preserves_similarity_scores(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Similarity scores returned by the vector store should be preserved.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
    )

    expected_scores = [
        score
        for _, score in search_results
    ]

    assert result.similarity_scores == expected_scores


@pytest.mark.asyncio
async def test_retrieve_preserves_documents(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Retrieved documents should remain unchanged.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
    )

    expected_documents = [
        document
        for document, _ in search_results
    ]

    assert result.documents == expected_documents

# --------------------------------------------------------------------------- #
# Result Validation
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_retrieve_returns_retrieval_result_instance(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Retriever should always return a RetrievalResult instance.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
    )

    assert isinstance(result, RetrievalResult)


@pytest.mark.asyncio
async def test_retrieve_respects_top_k_parameter(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Verify top_k is forwarded correctly.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    await retriever.retrieve(
        query="CRM",
        top_k=10,
    )

    kwargs = vector_store.similarity_search_with_scores.await_args.kwargs

    assert kwargs["k"] == 10


@pytest.mark.asyncio
async def test_retrieve_applies_score_threshold(
    retriever: Retriever,
    vector_store: AsyncMock,
):
    search_results = [
        (
            Document(
                page_content="High score",
                metadata={},
            ),
            0.95,
        ),
        (
            Document(
                page_content="Low score",
                metadata={},
            ),
            0.40,
        ),
    ]

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
        score_threshold=0.8,
    )

    assert len(result.documents) == 1
    assert result.similarity_scores == [0.95]


@pytest.mark.asyncio
async def test_retrieve_preserves_document_metadata(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    Metadata should remain unchanged after retrieval.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
    )

    for returned, expected in zip(
        result.documents,
        [doc for doc, _ in search_results],
    ):
        assert returned.metadata == expected.metadata


@pytest.mark.asyncio
async def test_retrieve_returns_correct_chunk_count(
    retriever: Retriever,
    vector_store: AsyncMock,
    search_results,
):
    """
    retrieved_chunks should equal the number of returned documents.
    """

    vector_store.similarity_search_with_scores.return_value = search_results

    result = await retriever.retrieve(
        query="CRM",
    )

    assert result.retrieved_chunks == len(search_results)

    assert len(result.documents) == len(search_results)

    assert len(result.similarity_scores) == len(search_results)