"""
tests/rag/test_pgvector_store.py
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.rag.exceptions import VectorStoreError
from app.rag.vectorstores.pgvector_store import PGVectorStore


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def repository() -> AsyncMock:
    """
    Mock DocumentChunkRepository.
    """
    repo = AsyncMock()
    repo.tenant_id = uuid4()
    return repo


@pytest.fixture
def embedding_provider() -> AsyncMock:
    """
    Mock embedding provider.
    """
    return AsyncMock()


@pytest.fixture
def vector_store(
    repository: AsyncMock,
    embedding_provider: AsyncMock,
) -> PGVectorStore:
    """
    PGVectorStore under test.
    """
    return PGVectorStore(
        repository=repository,
        embedding_provider=embedding_provider,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def make_chunk(
    *,
    index: int,
    content: str,
):
    tenant_id = uuid4()
    document_id = uuid4()

    document = SimpleNamespace(
        id=document_id,
        title="CRM Guide",
        filename="crm.pdf",
        mime_type="application/pdf",
        source_type="upload",
    )

    return SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        document_id=document_id,
        chunk_index=index,
        content=content,
        token_count=120,
        embedding=None,
        chunk_metadata={
            "section": "intro",
        },
        start_char=index * 100,
        end_char=index * 100 + 99,
        document=document,
    )


@pytest.fixture
def chunks():
    """
    Example ORM chunks.
    """
    return [
        make_chunk(
            index=0,
            content="CRM stands for Customer Relationship Management.",
        ),
        make_chunk(
            index=1,
            content="Sales opportunities are tracked in pipelines.",
        ),
    ]


# --------------------------------------------------------------------------- #
# index_chunks()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_index_chunks_success(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Embeddings should be generated and persisted.
    """

    embeddings = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    embedding_provider.embed_documents.return_value = embeddings

    await vector_store.index_chunks(chunks)

    embedding_provider.embed_documents.assert_awaited_once_with(
        [
            chunk.content
            for chunk in chunks
        ]
    )

    repository.update_embeddings.assert_awaited_once_with(
        chunks,
        embeddings,
    )


@pytest.mark.asyncio
async def test_index_chunks_empty_list(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    Empty chunk list should be ignored.
    """

    await vector_store.index_chunks([])

    embedding_provider.embed_documents.assert_not_awaited()

    repository.update_embeddings.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_chunks_embedding_count_mismatch(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Number of embeddings must equal number of chunks.
    """

    embedding_provider.embed_documents.return_value = [
        [0.1, 0.2],
    ]

    with pytest.raises(VectorStoreError):
        await vector_store.index_chunks(chunks)

    repository.update_embeddings.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_chunks_embedding_provider_failure(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Embedding provider failures should become VectorStoreError.
    """

    embedding_provider.embed_documents.side_effect = RuntimeError(
        "Embedding service unavailable"
    )

    with pytest.raises(VectorStoreError):
        await vector_store.index_chunks(chunks)

    repository.update_embeddings.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_chunks_repository_failure(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Repository failures should become VectorStoreError.
    """

    embedding_provider.embed_documents.return_value = [
        [0.1],
        [0.2],
    ]

    repository.update_embeddings.side_effect = RuntimeError(
        "Database failure"
    )

    with pytest.raises(VectorStoreError):
        await vector_store.index_chunks(chunks)


@pytest.mark.asyncio
async def test_index_chunks_preserves_chunk_order(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Chunk ordering should not change.
    """

    embeddings = [
        [1.0],
        [2.0],
    ]

    embedding_provider.embed_documents.return_value = embeddings

    await vector_store.index_chunks(chunks)

    args = repository.update_embeddings.await_args.args

    assert args[0][0] is chunks[0]
    assert args[0][1] is chunks[1]

    assert args[1] == embeddings

# --------------------------------------------------------------------------- #
# similarity_search()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_similarity_search_success(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    Similarity search should return LangChain Documents.
    """

    embedding_provider.embed_query.return_value = [
        0.11,
        0.22,
        0.33,
    ]

    repository.similarity_search.return_value = chunks

    results = await vector_store.similarity_search(
        query="What is CRM?",
        k=5,
    )

    embedding_provider.embed_query.assert_awaited_once_with(
        "What is CRM?"
    )

    repository.similarity_search.assert_awaited_once_with(
        [0.11, 0.22, 0.33],
        limit=5,
        document_id=None,
    )

    assert len(results) == 2

    assert all(
        isinstance(doc, Document)
        for doc in results
    )


@pytest.mark.asyncio
async def test_similarity_search_document_filter(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    document_id should be forwarded to repository.
    """

    document_id = uuid4()

    embedding_provider.embed_query.return_value = [0.5]

    repository.similarity_search.return_value = []

    await vector_store.similarity_search(
        query="CRM",
        document_id=document_id,
    )

    kwargs = repository.similarity_search.await_args.kwargs

    assert kwargs["document_id"] == document_id


@pytest.mark.asyncio
async def test_similarity_search_empty_results(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    Empty repository results should return [].
    """

    embedding_provider.embed_query.return_value = [0.5]

    repository.similarity_search.return_value = []

    results = await vector_store.similarity_search(
        query="Unknown",
    )

    assert results == []


@pytest.mark.asyncio
async def test_similarity_search_empty_query(
    vector_store: PGVectorStore,
):
    """
    Empty query should raise VectorStoreError.
    """

    with pytest.raises(VectorStoreError):
        await vector_store.similarity_search(
            query="",
        )


@pytest.mark.asyncio
async def test_similarity_search_whitespace_query(
    vector_store: PGVectorStore,
):
    """
    Whitespace-only query should raise VectorStoreError.
    """

    with pytest.raises(VectorStoreError):
        await vector_store.similarity_search(
            query="     ",
        )


@pytest.mark.asyncio
async def test_similarity_search_embedding_failure(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    Embedding failures should be wrapped.
    """

    embedding_provider.embed_query.side_effect = RuntimeError(
        "Embedding backend unavailable"
    )

    with pytest.raises(VectorStoreError):
        await vector_store.similarity_search(
            query="CRM",
        )

    repository.similarity_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_similarity_search_repository_failure(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    Repository failures should become VectorStoreError.
    """

    embedding_provider.embed_query.return_value = [
        0.5,
    ]

    repository.similarity_search.side_effect = RuntimeError(
        "Database error"
    )

    with pytest.raises(VectorStoreError):
        await vector_store.similarity_search(
            query="CRM",
        )


# --------------------------------------------------------------------------- #
# similarity_search_with_scores()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_similarity_search_with_scores(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
    chunks,
):
    """
    similarity_search_with_scores should return
    (Document, float) tuples.
    """

    embedding_provider.embed_query.return_value = [
        0.5,
    ]

    repository.similarity_search.return_value = chunks

    results = (
        await vector_store.similarity_search_with_scores(
            query="CRM",
        )
    )

    assert len(results) == 2

    for document, score in results:
        assert isinstance(document, Document)
        assert isinstance(score, float)

    assert results[0][1] == 1.0
    assert results[1][1] == 1.0


@pytest.mark.asyncio
async def test_similarity_search_with_scores_document_filter(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    document_id should propagate through
    similarity_search_with_scores().
    """

    embedding_provider.embed_query.return_value = [
        0.5,
    ]

    repository.similarity_search.return_value = []

    document_id = uuid4()

    await vector_store.similarity_search_with_scores(
        query="CRM",
        document_id=document_id,
    )

    kwargs = repository.similarity_search.await_args.kwargs

    assert kwargs["document_id"] == document_id


@pytest.mark.asyncio
async def test_similarity_search_with_scores_empty_results(
    vector_store: PGVectorStore,
    repository: AsyncMock,
    embedding_provider: AsyncMock,
):
    """
    Empty repository response should remain empty.
    """

    embedding_provider.embed_query.return_value = [
        0.5,
    ]

    repository.similarity_search.return_value = []

    results = (
        await vector_store.similarity_search_with_scores(
            query="CRM",
        )
    )

    assert results == []

# --------------------------------------------------------------------------- #
# _to_document()
# --------------------------------------------------------------------------- #


def test_to_document_basic(chunks):
    """
    ORM chunk should be converted into a LangChain Document.
    """

    chunk = chunks[0]

    document = PGVectorStore._to_document(chunk)

    assert isinstance(document, Document)

    assert document.page_content == chunk.content

    assert document.metadata["chunk_id"] == str(chunk.id)

    assert (
        document.metadata["document_id"]
        == str(chunk.document_id)
    )

    assert (
        document.metadata["tenant_id"]
        == str(chunk.tenant_id)
    )

    assert (
        document.metadata["chunk_index"]
        == chunk.chunk_index
    )

    assert (
        document.metadata["token_count"]
        == chunk.token_count
    )

    assert (
        document.metadata["start_char"]
        == chunk.start_char
    )

    assert (
        document.metadata["end_char"]
        == chunk.end_char
    )


def test_to_document_preserves_chunk_metadata(
    chunks,
):
    """
    chunk_metadata should be merged into Document metadata.
    """

    chunk = chunks[0]

    chunk.chunk_metadata = {
        "section": "Introduction",
        "page": 3,
        "heading": "CRM Basics",
    }

    document = PGVectorStore._to_document(chunk)

    assert document.metadata["section"] == "Introduction"

    assert document.metadata["page"] == 3

    assert document.metadata["heading"] == "CRM Basics"


def test_to_document_without_chunk_metadata(
    chunks,
):
    """
    None metadata should be handled gracefully.
    """

    chunk = chunks[0]

    chunk.chunk_metadata = None

    document = PGVectorStore._to_document(chunk)

    assert "section" not in document.metadata

    assert (
        document.metadata["chunk_index"]
        == chunk.chunk_index
    )


def test_to_document_adds_document_metadata(
    chunks,
):
    """
    Related KnowledgeDocument fields should be copied.
    """

    chunk = chunks[0]

    document = PGVectorStore._to_document(chunk)

    assert document.metadata["title"] == "CRM Guide"

    assert document.metadata["filename"] == "crm.pdf"

    assert (
        document.metadata["mime_type"]
        == "application/pdf"
    )

    assert (
        document.metadata["source_type"]
        == "upload"
    )


def test_to_document_without_relationship(
    chunks,
):
    """
    Missing document relationship should not fail.
    """

    chunk = chunks[0]

    chunk.document = None

    document = PGVectorStore._to_document(chunk)

    assert isinstance(document, Document)

    assert (
        document.metadata["chunk_id"]
        == str(chunk.id)
    )

    assert "title" not in document.metadata

    assert "filename" not in document.metadata

    assert "mime_type" not in document.metadata

    assert "source_type" not in document.metadata


def test_to_document_preserves_page_content(
    chunks,
):
    """
    Chunk content should become page_content.
    """

    chunk = chunks[1]

    document = PGVectorStore._to_document(chunk)

    assert (
        document.page_content
        == chunk.content
    )


def test_to_document_metadata_types(
    chunks,
):
    """
    Metadata values should have expected types.
    """

    document = PGVectorStore._to_document(
        chunks[0]
    )

    assert isinstance(
        document.metadata["chunk_id"],
        str,
    )

    assert isinstance(
        document.metadata["document_id"],
        str,
    )

    assert isinstance(
        document.metadata["tenant_id"],
        str,
    )

    assert isinstance(
        document.metadata["chunk_index"],
        int,
    )

    assert isinstance(
        document.metadata["token_count"],
        int,
    )

    assert isinstance(
        document.metadata["start_char"],
        int,
    )

    assert isinstance(
        document.metadata["end_char"],
        int,
    )


def test_to_document_empty_chunk_metadata(
    chunks,
):
    """
    Empty metadata dictionary should be supported.
    """

    chunk = chunks[0]

    chunk.chunk_metadata = {}

    document = PGVectorStore._to_document(chunk)

    assert isinstance(document, Document)

    assert (
        document.metadata["chunk_index"]
        == chunk.chunk_index
    )


def test_to_document_preserves_extra_metadata(
    chunks,
):
    """
    Arbitrary metadata should be preserved.
    """

    chunk = chunks[0]

    chunk.chunk_metadata = {
        "language": "en",
        "department": "sales",
        "version": 2,
        "is_public": True,
    }

    document = PGVectorStore._to_document(chunk)

    assert document.metadata["language"] == "en"

    assert document.metadata["department"] == "sales"

    assert document.metadata["version"] == 2

    assert document.metadata["is_public"] is True