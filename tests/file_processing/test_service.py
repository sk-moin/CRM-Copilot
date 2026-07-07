"""Tests for DocumentProcessingService."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest

from app.file_processing.service import DocumentProcessingService
from app.file_processing.models.extracted_document import ExtractedDocument
from app.file_processing.chunkers.models import TextChunk
from app.file_processing.embeddings.models import EmbeddingResult
from packages.database.models.enums import DocumentProcessingStatus


@pytest.fixture
def knowledge_repo():
    return AsyncMock()


@pytest.fixture
def chunk_repo():
    return AsyncMock()


@pytest.fixture
def parser():
    return Mock()


@pytest.fixture
def parser_factory(parser):
    factory = Mock()
    factory.get_parser.return_value = parser
    return factory


@pytest.fixture
def chunker():
    return Mock()


@pytest.fixture
def embedding_provider():
    provider = AsyncMock()
    return provider


@pytest.fixture
def service(
    knowledge_repo,
    chunk_repo,
    parser_factory,
    chunker,
    embedding_provider,
):
    return DocumentProcessingService(
        knowledge_repo=knowledge_repo,
        chunk_repo=chunk_repo,
        parser_factory=parser_factory,
        chunker=chunker,
        embedding_provider=embedding_provider,
    )


@pytest.fixture
def extracted_document():
    return ExtractedDocument(
        text="This is a test document.",
        filename="sample.txt",
        mime_type="text/plain",
    )


@pytest.fixture
def text_chunks():
    return [
        TextChunk(
            text="Chunk one",
            chunk_index=0,
            start_char=0,
            end_char=9,
            token_count=2,
            metadata={},
        ),
        TextChunk(
            text="Chunk two",
            chunk_index=1,
            start_char=10,
            end_char=19,
            token_count=2,
            metadata={},
        ),
    ]


@pytest.fixture
def embedding_results():
    return [
        EmbeddingResult(
            embedding=[0.1] * 384,
            model_name="test-model",
            dimensions=384,
        ),
        EmbeddingResult(
            embedding=[0.2] * 384,
            model_name="test-model",
            dimensions=384,
        ),
    ]


@pytest.mark.asyncio
async def test_process_document_success(
    service,
    knowledge_repo,
    chunk_repo,
    parser_factory,
    chunker,
    embedding_provider,
    parser,
    extracted_document,
    text_chunks,
    embedding_results,
):
    """Successful document processing."""

    tenant_id = uuid4()

    document = Mock()
    document.id = uuid4()
    document.processing_status = DocumentProcessingStatus.UPLOADED

    knowledge_repo.create.return_value = document

    parser.parse.return_value = extracted_document

    chunker.chunk.return_value = text_chunks

    embedding_provider.embed_texts.return_value = embedding_results

    await service.process_document(
        Path("sample.txt"),
        tenant_id,
    )

    knowledge_repo.create.assert_called_once()

    parser_factory.get_parser.assert_called_once()

    parser.parse.assert_called_once()

    chunker.chunk.assert_called_once()

    embedding_provider.embed_texts.assert_called_once()

    chunk_repo.bulk_create.assert_called_once()

    assert knowledge_repo.update_status.call_count >= 2


@pytest.mark.asyncio
async def test_process_empty_document(
    service,
    knowledge_repo,
    parser,
):
    """Empty documents should raise ValueError."""

    tenant_id = uuid4()

    document = Mock()
    document.id = uuid4()

    knowledge_repo.create.return_value = document

    parser.parse.return_value = ExtractedDocument(
        text="",
        filename="empty.txt",
    )

    with pytest.raises(ValueError):
        await service.process_document(
            Path("empty.txt"),
            tenant_id,
        )


@pytest.mark.asyncio
async def test_reprocess_document(
    service,
    knowledge_repo,
    chunk_repo,
):
    """Existing document should be reprocessed."""

    document = Mock()

    document.id = uuid4()
    document.filename = "sample.txt"
    document.storage_path = "sample.txt"
    document.tenant_id = uuid4()

    knowledge_repo.get_with_chunks.return_value = document

    service.process_document = AsyncMock(return_value=document)

    await service.reprocess_document(document.id)

    knowledge_repo.get_with_chunks.assert_called_once()

    chunk_repo.delete_by_document_id.assert_called_once_with(document.id)

    service.process_document.assert_called_once()


@pytest.mark.asyncio
async def test_reprocess_missing_document(
    service,
    knowledge_repo,
):
    """Missing document should raise ValueError."""

    knowledge_repo.get_with_chunks.return_value = None

    with pytest.raises(ValueError):
        await service.reprocess_document(uuid4())


@pytest.mark.asyncio
async def test_processing_failure_updates_status(
    service,
    knowledge_repo,
    parser,
):
    """Failure should mark document as FAILED."""

    tenant_id = uuid4()

    document = Mock()
    document.id = uuid4()

    knowledge_repo.create.return_value = document

    parser.parse.side_effect = RuntimeError("Parser failed")

    with pytest.raises(RuntimeError):
        await service.process_document(
            Path("broken.pdf"),
            tenant_id,
        )

    knowledge_repo.update_status.assert_called()


@pytest.mark.asyncio
async def test_embedding_called_for_all_chunks(
    service,
    embedding_provider,
    chunker,
    parser,
    knowledge_repo,
    extracted_document,
    text_chunks,
    embedding_results,
):
    """Embedding provider should receive every chunk."""

    tenant_id = uuid4()

    document = Mock()
    document.id = uuid4()

    knowledge_repo.create.return_value = document

    parser.parse.return_value = extracted_document

    chunker.chunk.return_value = text_chunks

    embedding_provider.embed_texts.return_value = embedding_results

    await service.process_document(
        Path("sample.txt"),
        tenant_id,
    )

    texts = [chunk.text for chunk in text_chunks]

    embedding_provider.embed_texts.assert_called_once_with(texts)


@pytest.mark.asyncio
async def test_bulk_create_receives_correct_number_of_chunks(
    service,
    knowledge_repo,
    chunk_repo,
    parser,
    chunker,
    embedding_provider,
    extracted_document,
    text_chunks,
    embedding_results,
):
    """Repository should receive one DB record per chunk."""

    tenant_id = uuid4()

    document = Mock()
    document.id = uuid4()

    knowledge_repo.create.return_value = document

    parser.parse.return_value = extracted_document

    chunker.chunk.return_value = text_chunks

    embedding_provider.embed_texts.return_value = embedding_results

    await service.process_document(
        Path("sample.txt"),
        tenant_id,
    )

    args = chunk_repo.bulk_create.call_args.args[0]

    assert len(args) == len(text_chunks)