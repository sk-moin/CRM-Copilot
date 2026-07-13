"""
tests/rag/test_embedding_provider.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.embeddings import Embeddings

from app.rag.embeddings.embedding_provider import (
    EmbeddingProvider,
    create_embedding_provider,
)
from app.rag.exceptions import EmbeddingError

VECTOR_SIZE = 384


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------


@pytest.fixture
def mock_embeddings():
    embeddings = MagicMock(spec=Embeddings)

    embeddings.aembed_query = AsyncMock(
        return_value=[0.1] * VECTOR_SIZE
    )

    embeddings.aembed_documents = AsyncMock(
        side_effect=lambda texts: [
            [float(i)] * VECTOR_SIZE
            for i, _ in enumerate(texts)
        ]
    )

    return embeddings


@pytest.fixture
def provider(
    mock_embeddings,
) -> EmbeddingProvider:
    """
    EmbeddingProvider backed by mocked embeddings.
    """
    return EmbeddingProvider(mock_embeddings)


@pytest.fixture
def sample_query():
    return "What is Customer Relationship Management?"


@pytest.fixture
def sample_documents():
    return [
        "Customer Relationship Management improves customer engagement.",
        "Sales pipelines help track opportunities.",
        "Leads can be converted into customers.",
    ]


# -------------------------------------------------------------------------
# embed_query()
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_query_success(
    provider,
    sample_query,
):
    embedding = await provider.embed_query(sample_query)

    assert isinstance(embedding, list)
    assert len(embedding) == VECTOR_SIZE
    assert all(isinstance(x, float) for x in embedding)

    provider.client.aembed_query.assert_awaited_once_with(
        sample_query
    )


# -------------------------------------------------------------------------
# embed_documents()
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_documents_success(
    provider,
    sample_documents,
):
    embeddings = await provider.embed_documents(
        sample_documents
    )

    assert len(embeddings) == len(sample_documents)

    for embedding in embeddings:
        assert len(embedding) == VECTOR_SIZE
        assert all(isinstance(x, float) for x in embedding)

    provider.client.aembed_documents.assert_awaited_once_with(
        sample_documents
    )


@pytest.mark.asyncio
async def test_embed_single_document(
    provider,
):
    embeddings = await provider.embed_documents(
        ["CRM improves customer relationships."]
    )

    assert len(embeddings) == 1
    assert len(embeddings[0]) == VECTOR_SIZE


@pytest.mark.asyncio
async def test_embed_empty_document_list(
    provider,
):
    embeddings = await provider.embed_documents([])

    assert embeddings == []

    provider.client.aembed_documents.assert_awaited_once_with(
        []
    )


@pytest.mark.asyncio
async def test_embed_documents_preserves_order(
    provider,
    sample_documents,
):
    embeddings = await provider.embed_documents(
        sample_documents
    )

    assert embeddings[0][0] == 0.0
    assert embeddings[1][0] == 1.0
    assert embeddings[2][0] == 2.0


# -------------------------------------------------------------------------
# Factory
# -------------------------------------------------------------------------


@patch("app.rag.embeddings.embedding_provider.OpenAIEmbeddings")
@patch("app.rag.embeddings.embedding_provider.settings")
def test_create_embedding_provider(
    mock_settings,
    mock_openai,
):
    mock_settings.EMBEDDING_PROVIDER = "openai"
    mock_settings.EMBEDDING_MODEL = "text-embedding-3-small"
    mock_settings.OPENAI_API_KEY = "test-key"
    mock_settings.OPENAI_BASE_URL = "https://api.openai.com/v1"

    mock_openai.return_value = MagicMock(spec=Embeddings)

    provider = create_embedding_provider()

    assert isinstance(provider, EmbeddingProvider)

    mock_openai.assert_called_once_with(
        model="text-embedding-3-small",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
    )


# -------------------------------------------------------------------------
# Dimensions
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embedding_dimensions_are_consistent(
    provider,
    sample_documents,
):
    embeddings = await provider.embed_documents(
        sample_documents
    )

    assert {len(e) for e in embeddings} == {
        VECTOR_SIZE
    }


@pytest.mark.asyncio
async def test_query_and_document_dimensions_match(
    provider,
    sample_query,
    sample_documents,
):
    query_embedding = await provider.embed_query(
        sample_query
    )

    document_embedding = (
        await provider.embed_documents(
            [sample_documents[0]]
        )
    )[0]

    assert len(query_embedding) == len(
        document_embedding
    )


@pytest.mark.asyncio
async def test_embeddings_are_numeric(
    provider,
    sample_documents,
):
    embeddings = await provider.embed_documents(
        sample_documents
    )

    for embedding in embeddings:
        assert all(
            isinstance(x, float)
            for x in embedding
        )


# -------------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_query_propagates_errors(
    provider,
):
    provider.client.aembed_query.side_effect = RuntimeError(
        "Backend failed"
    )

    with pytest.raises(EmbeddingError):
        await provider.embed_query("hello")


@pytest.mark.asyncio
async def test_embed_documents_propagates_errors(
    provider,
):
    provider.client.aembed_documents.side_effect = RuntimeError(
        "Backend failed"
    )

    with pytest.raises(EmbeddingError):
        await provider.embed_documents(["hello"])