"""Tests for KnowledgeDocumentRepository."""

from datetime import datetime
from uuid import uuid4

import pytest

from packages.database.models.enums import DocumentProcessingStatus
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)


@pytest.fixture
async def repository(async_session, tenant, organization, user):
    """Create repository instance."""
    return KnowledgeDocumentRepository(async_session, tenant.id)


@pytest.mark.asyncio
async def test_list_by_status(repository, organization, user):
    """Should list only documents with the requested status."""
    await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Doc 1",
        filename="doc1.pdf",
        storage_path="/tmp/doc1.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
        processing_status=DocumentProcessingStatus.READY,
    )

    await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Doc 2",
        filename="doc2.pdf",
        storage_path="/tmp/doc2.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
        processing_status=DocumentProcessingStatus.FAILED,
    )

    docs = await repository.list_by_status(DocumentProcessingStatus.READY)

    assert len(docs) == 1
    assert docs[0].title == "Doc 1"


@pytest.mark.asyncio
async def test_update_status(repository, organization, user):
    """Should update processing status."""
    document = await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Test",
        filename="test.pdf",
        storage_path="/tmp/test.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=123,
    )

    updated = await repository.update_status(
        document.id,
        DocumentProcessingStatus.READY,
    )

    assert updated is not None
    assert updated.processing_status == DocumentProcessingStatus.READY


@pytest.mark.asyncio
async def test_update_processing_info(repository, organization, user):
    """Should update processing metadata."""
    document = await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Test",
        filename="test.pdf",
        storage_path="/tmp/test.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=123,
    )

    now = datetime.utcnow()

    updated = await repository.update_processing_info(
        document.id,
        chunk_count=8,
        processed_at=now,
        error_message=None,
    )

    assert updated is not None
    assert updated.chunk_count == 8
    assert updated.processed_at == now


@pytest.mark.asyncio
async def test_update_processing_error(repository, organization, user):
    """Should store processing error."""
    document = await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Broken",
        filename="broken.pdf",
        storage_path="/tmp/broken.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    updated = await repository.update_processing_info(
        document.id,
        error_message="Parsing failed",
    )

    assert updated is not None
    assert updated.error_message == "Parsing failed"


@pytest.mark.asyncio
async def test_list_by_document_type(repository, organization, user):
    """Should filter by document type."""
    await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="PDF",
        filename="a.pdf",
        storage_path="/tmp/a.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="DOCX",
        filename="b.docx",
        storage_path="/tmp/b.docx",
        document_type="docx",
        source_type="upload",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=100,
    )

    docs = await repository.list_by_document_type("pdf")

    assert len(docs) == 1
    assert docs[0].document_type == "pdf"


@pytest.mark.asyncio
async def test_get_with_chunks(repository, organization, user):
    """Should load document with chunk relationship."""
    document = await repository.create(
        organization_id=organization.id,
        owner_id=user.id,
        title="Knowledge",
        filename="knowledge.pdf",
        storage_path="/tmp/knowledge.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    loaded = await repository.get_with_chunks(document.id)

    assert loaded is not None
    assert loaded.id == document.id
    assert hasattr(loaded, "chunks")