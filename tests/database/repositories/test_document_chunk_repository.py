"""Tests for DocumentChunkRepository."""

from uuid import uuid4

import pytest

from packages.database.models.document_chunk import DocumentChunk
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
import pytest_asyncio

from packages.database.models.knowledge_document import KnowledgeDocument
from packages.database.models.enums import DocumentProcessingStatus

@pytest.fixture
async def repository(async_session, tenant):
    """Create repository instance."""
    return DocumentChunkRepository(async_session, tenant.id)


@pytest.mark.asyncio
async def test_bulk_create(repository,knowledge_document):
    document_id = knowledge_document.id

    chunks = [
    {
        "document_id": document_id,
        "chunk_index": 0,
        "content": "First chunk",
        "token_count": 10,
        "embedding": [0.1] * 384,
        "chunk_metadata": {"page": 1},
        "start_char": 0,
        "end_char": 11,
    },
    {
        "document_id": document_id,
        "chunk_index": 1,
        "content": "Second chunk",
        "token_count": 12,
        "embedding": [0.2] * 384,
        "chunk_metadata": {"page": 2},
        "start_char": 12,
        "end_char": 24,
    },
    ]

    result = await repository.bulk_create(chunks)

    assert len(result) == 2
    assert result[0].chunk_index == 0
    assert result[1].chunk_index == 1


@pytest.mark.asyncio
async def test_get_by_document_id(repository,knowledge_document):
    document_id = knowledge_document.id

    await repository.create(
        document_id=document_id,
        chunk_index=1,
        content="Second",
        token_count=5,
        start_char=6,
        end_char=11,
    )

    await repository.create(
        document_id=document_id,
        chunk_index=0,
        content="First",
        token_count=5,
        start_char=0,
        end_char=5,
    )

    chunks = await repository.get_by_document_id(document_id)

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


@pytest.mark.asyncio
async def test_delete_by_document_id(
    repository,
    knowledge_document,
):
    document_id = knowledge_document.id

    await repository.create(
        document_id=document_id,
        chunk_index=0,
        content="Chunk",
        token_count=5,
        start_char=0,
        end_char=5,
    )

    assert len(await repository.get_by_document_id(document_id)) == 1

    await repository.delete_by_document_id(document_id)

    chunks = await repository.get_by_document_id(document_id)

    assert chunks == []


@pytest.mark.asyncio
async def test_filter_by_metadata(
    repository,
    knowledge_document,
):
    document_id = knowledge_document.id

    await repository.create(
        document_id=document_id,
        chunk_index=0,
        content="Page 1",
        token_count=5,
        chunk_metadata={"page": 1},
        start_char=0,
        end_char=6,
    )

    await repository.create(
        document_id=document_id,
        chunk_index=1,
        content="Page 2",
        token_count=5,
        chunk_metadata={"page": 2},
        start_char=7,
        end_char=13,
    )

    results = await repository.filter_by_metadata({"page": 1})

    assert len(results) == 1
    assert results[0].chunk_metadata["page"] == 1


@pytest.mark.asyncio
async def test_similarity_search(
    repository,
    knowledge_document,
):
    document_id = knowledge_document.id

    await repository.create(
        document_id=document_id,
        chunk_index=0,
        content="Vector chunk",
        token_count=10,
        embedding=[0.1] * 384,
        start_char=0,
        end_char=12,
    )

    results = await repository.similarity_search(
        [0.1] * 384,
        limit=5,
    )

    assert isinstance(results, list)


@pytest_asyncio.fixture
async def knowledge_document(
    async_session,
    tenant,
    organization,
    user,
):
    document = KnowledgeDocument(
        tenant_id=tenant.id,
        organization_id=organization.id,
        owner_id=user.id,

        title="Sample Document",
        filename="sample.pdf",
        storage_path="sample.pdf",

        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",

        file_size=1024,
    )

    async_session.add(document)
    await async_session.flush()

    return document