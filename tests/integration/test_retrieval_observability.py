"""Integration tests for Retrieval Observability."""

from __future__ import annotations

import pytest

from app.services.retrieval_trace_service import RetrievalTraceService
from app.services.retrieved_chunk_service import RetrievedChunkService

from packages.database.models.knowledge_document import KnowledgeDocument
from packages.database.models.document_chunk import DocumentChunk

from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)


@pytest.mark.asyncio
async def test_create_trace_and_retrieve(
    async_session,
    seeded_tenant,
    seeded_organization,
):
    """Create a retrieval trace and fetch it back."""

    repository = RetrievalTraceRepository(
        async_session,
        seeded_tenant.id,
    )

    service = RetrievalTraceService(repository)

    trace = await service.create_trace(
        conversation_id=None,
        query="What is RAG?",
        embedding_model="text-embedding-3-small",
        vector_store="pgvector",
    )

    await async_session.commit()

    loaded = await service.get_trace(trace.id)

    assert loaded is not None
    assert loaded.id == trace.id
    assert loaded.query == "What is RAG?"
    assert loaded.embedding_model == "text-embedding-3-small"
    assert loaded.vector_store == "pgvector"


@pytest.mark.asyncio
async def test_create_trace_with_chunks(
    async_session,
    seeded_tenant,
    seeded_organization,
):
    """Create a retrieval trace together with retrieved chunks."""

    # ------------------------------------------------------------------
    # Seed KnowledgeDocument
    # ------------------------------------------------------------------

    document = KnowledgeDocument(
        tenant_id=seeded_tenant.id,
        organization_id=seeded_organization.id,
        owner_id=None,
        title="Embeddings",
        filename="embeddings.pdf",
        storage_path="/tmp/embeddings.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    async_session.add(document)
    await async_session.flush()

    # ------------------------------------------------------------------
    # Seed DocumentChunk
    # ------------------------------------------------------------------

    chunk = DocumentChunk(
        tenant_id=seeded_tenant.id,
        document_id=document.id,
        chunk_index=0,
        content="Embeddings convert text into vectors.",
        token_count=6,
        start_char=0,
        end_char=36,
    )

    async_session.add(chunk)
    await async_session.flush()

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    trace_repo = RetrievalTraceRepository(
        async_session,
        seeded_tenant.id,
    )

    chunk_repo = RetrievedChunkRepository(
        async_session,
        seeded_tenant.id,
    )

    trace_service = RetrievalTraceService(trace_repo)
    chunk_service = RetrievedChunkService(chunk_repo)

    # ------------------------------------------------------------------
    # Create trace
    # ------------------------------------------------------------------

    trace = await trace_service.create_trace(
        conversation_id=None,
        query="Explain embeddings",
    )

    # ------------------------------------------------------------------
    # Create retrieved chunks
    # ------------------------------------------------------------------

    await chunk_service.bulk_create(
        [
            {
                "trace_id": trace.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "rank": 1,
                "similarity_score": 0.95,
                "chunk_preview": "Embedding chunk",
            },
            {
                "trace_id": trace.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "rank": 2,
                "similarity_score": 0.90,
                "chunk_preview": "Vector search",
            },
        ]
    )

    await async_session.commit()

    chunks = await chunk_service.get_by_trace(trace.id)

    assert len(chunks) == 2

    assert chunks[0].trace_id == trace.id
    assert chunks[0].document_id == document.id
    assert chunks[0].chunk_id == chunk.id
    assert chunks[0].rank == 1
    assert chunks[0].similarity_score == 0.95

    assert chunks[1].rank == 2
    assert chunks[1].similarity_score == 0.90