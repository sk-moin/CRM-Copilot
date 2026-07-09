"""Integration tests for retrieval logging workflow."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.retrieval_trace_service import RetrievalTraceService
from app.services.retrieved_chunk_service import RetrievedChunkService

from packages.database.models.knowledge_document import (
    KnowledgeDocument,
)
from packages.database.models.document_chunk import (
    DocumentChunk,
)

from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)


@pytest.mark.asyncio
async def test_complete_retrieval_logging_flow(
    async_session,
    seeded_tenant,
    seeded_organization,
):
    """Complete retrieval logging workflow."""

    # ------------------------------------------------------------------
    # Seed document
    # ------------------------------------------------------------------

    document = KnowledgeDocument(
        tenant_id=seeded_tenant.id,
        organization_id=seeded_organization.id,
        owner_id=None,
        title="RAG Document",
        filename="rag.pdf",
        storage_path="/tmp/rag.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    async_session.add(document)
    await async_session.flush()

    chunk = DocumentChunk(
        tenant_id=seeded_tenant.id,
        document_id=document.id,
        chunk_index=0,
        content="This is a retrieved chunk.",
        token_count=6,
        start_char=0,
        end_char=25,
    )

    async_session.add(chunk)
    await async_session.flush()

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    trace_repository = RetrievalTraceRepository(
        async_session,
        seeded_tenant.id,
    )

    chunk_repository = RetrievedChunkRepository(
        async_session,
        seeded_tenant.id,
    )

    trace_service = RetrievalTraceService(trace_repository)
    chunk_service = RetrievedChunkService(chunk_repository)

    # ------------------------------------------------------------------
    # Create trace
    # ------------------------------------------------------------------

    trace = await trace_service.create_trace(
        conversation_id=None,
        query="How does pgvector work?",
        embedding_model="text-embedding-3-small",
        vector_store="pgvector",
    )

    # ------------------------------------------------------------------
    # Log retrieved chunks
    # ------------------------------------------------------------------

    await chunk_service.bulk_create(
        [
            {
                "trace_id": trace.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "rank": 1,
                "similarity_score": 0.97,
                "chunk_preview": "Chunk A",
            },
            {
                "trace_id": trace.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "rank": 2,
                "similarity_score": 0.93,
                "chunk_preview": "Chunk B",
            },
        ]
    )

    await trace_service.update_trace(
        trace.id,
        status="success",
        retrieved_chunks=2,
        total_latency_ms=143.2,
    )

    await async_session.commit()

    loaded_trace = await trace_service.get_trace(trace.id)
    loaded_chunks = await chunk_service.get_by_trace(trace.id)

    assert loaded_trace is not None
    assert loaded_trace.retrieved_chunks == 2
    assert loaded_trace.total_latency_ms == 143.2
    assert loaded_trace.status.value == "success"

    assert len(loaded_chunks) == 2
    assert loaded_chunks[0].rank == 1
    assert loaded_chunks[1].rank == 2


@pytest.mark.asyncio
async def test_delete_trace_cascades_chunks(
    async_session,
    seeded_tenant,
    seeded_organization,
):
    """Deleting a trace should remove retrieved chunks."""

    # ------------------------------------------------------------------
    # Seed document
    # ------------------------------------------------------------------

    document = KnowledgeDocument(
        tenant_id=seeded_tenant.id,
        organization_id=seeded_organization.id,
        owner_id=None,
        title="Cascade Document",
        filename="cascade.pdf",
        storage_path="/tmp/cascade.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    async_session.add(document)
    await async_session.flush()

    chunk = DocumentChunk(
        tenant_id=seeded_tenant.id,
        document_id=document.id,
        chunk_index=0,
        content="Cascade chunk",
        token_count=2,
        start_char=0,
        end_char=13,
    )

    async_session.add(chunk)
    await async_session.flush()

    trace_repository = RetrievalTraceRepository(
        async_session,
        seeded_tenant.id,
    )

    chunk_repository = RetrievedChunkRepository(
        async_session,
        seeded_tenant.id,
    )

    trace_service = RetrievalTraceService(trace_repository)
    chunk_service = RetrievedChunkService(chunk_repository)

    trace = await trace_service.create_trace(
        conversation_id=None,
        query="Cascade test",
    )

    await chunk_service.bulk_create(
        [
            {
                "trace_id": trace.id,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "rank": 1,
                "similarity_score": 0.88,
                "chunk_preview": "Chunk",
            }
        ]
    )

    await async_session.commit()

    deleted = await trace_service.delete_trace(trace.id)

    await async_session.commit()

    assert deleted is True

    chunks = await chunk_service.get_by_trace(trace.id)

    assert chunks == []