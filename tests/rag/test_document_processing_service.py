"""
tests/rag/test_document_processing_service.py
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.rag.document_processing_service import (
    DocumentProcessingService,
)
from app.rag.models.document_processing_request import (
    DocumentProcessingRequest,
)
from app.rag.exceptions import ChunkingError, DocumentParsingError
from packages.database.models.enums import (
    DocumentProcessingStatus,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def parser() -> MagicMock:
    return MagicMock()


@pytest.fixture
def splitter() -> MagicMock:
    return MagicMock()


@pytest.fixture
def document_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def chunk_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def vector_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    vector_store: AsyncMock,
) -> DocumentProcessingService:
    return DocumentProcessingService(
        parser=parser,
        splitter=splitter,
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        vector_store=vector_store,
    )


@pytest.fixture
def processing_request() -> DocumentProcessingRequest:
    return DocumentProcessingRequest(
        tenant_id=uuid4(),
        org_id=uuid4(),
        owner_id=uuid4(),
        title="CRM Handbook",
        filename="crm.pdf",
        storage_path="/tmp/crm.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=4096,
    )


@pytest.fixture
def persisted_document():
    """The row as it comes back from create.

    The service reads the metadata off this, not off the request: by the time
    the worker processes a document the request is long gone.
    """

    return SimpleNamespace(
        id=uuid4(),
        title="CRM Handbook",
        filename="crm.pdf",
        storage_path="/tmp/crm.pdf",
        document_type="pdf",
    )


@pytest.fixture
def parsed_document():
    return SimpleNamespace(
        content=(
            "This is a sample document used for "
            "DocumentProcessingService tests."
        ),
    )


@pytest.fixture
def split_chunks():
    return [
        SimpleNamespace(
            page_content="Chunk 1",
            metadata={
                "page": 1,
                "start_index": 0,
            },
        ),
        SimpleNamespace(
            page_content="Chunk 2",
            metadata={
                "page": 1,
                "start_index": 51,
            },
        ),
    ]


@pytest.fixture
def created_chunks():
    return [
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(id=uuid4()),
    ]


async def _create_and_process(service, request, document_repository):
    """Upload then ingest, which is what the two halves add up to.

    The repository is a mock, so it has to be told to hand back the row it
    just "created" when the processing half looks it up.
    """

    document = await service.create_document(request)

    document_repository.get_by_id.return_value = document

    return await service.process_document(document.id)


# --------------------------------------------------------------------------- #
# Success
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_process_success(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    vector_store: AsyncMock,
    persisted_document,
    parsed_document,
    split_chunks,
    created_chunks,
):
    """
    Document is parsed, split, embedded and indexed successfully.
    """

    # ------------------------------------------------------------------ #
    # Arrange
    # ------------------------------------------------------------------ #

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.return_value = split_chunks

    chunk_repository.bulk_create.return_value = created_chunks

    vector_store.index_chunks.return_value = None

    # ------------------------------------------------------------------ #
    # Act
    # ------------------------------------------------------------------ #

    result = await _create_and_process(
            service, processing_request, document_repository
        )

    # ------------------------------------------------------------------ #
    # Assert parser
    # ------------------------------------------------------------------ #

    parser.parse.assert_called_once_with(
        processing_request.storage_path,
    )

    # ------------------------------------------------------------------ #
    # Assert splitter
    # ------------------------------------------------------------------ #

    splitter.split_text.assert_called_once()

    splitter_args = splitter.split_text.call_args

    assert (
        splitter_args.args[0]
        == parsed_document.content
    )

    metadata = splitter_args.kwargs["metadata"]

    assert metadata["document_id"] == str(
        persisted_document.id,
    )

    assert (
        metadata["filename"]
        == processing_request.filename
    )

    assert (
        metadata["title"]
        == processing_request.title
    )

    assert (
        metadata["document_type"]
        == processing_request.document_type
    )

    # ------------------------------------------------------------------ #
    # Assert repository interactions
    # ------------------------------------------------------------------ #

    document_repository.create.assert_awaited_once()

    document_repository.mark_processing.assert_awaited_once_with(
        persisted_document.id,
    )

    chunk_repository.bulk_create.assert_awaited_once()

    payload = (
        chunk_repository
        .bulk_create
        .call_args
        .args[0]
    )

    assert len(payload) == len(split_chunks)

    assert payload[0]["document_id"] == persisted_document.id
    assert payload[0]["content"] == "Chunk 1"
    assert payload[0]["chunk_index"] == 0

    assert payload[1]["document_id"] == persisted_document.id
    assert payload[1]["content"] == "Chunk 2"
    assert payload[1]["chunk_index"] == 1

    # ------------------------------------------------------------------ #
    # Assert vector indexing
    # ------------------------------------------------------------------ #

    vector_store.index_chunks.assert_awaited_once_with(
        created_chunks,
    )

    # ------------------------------------------------------------------ #
    # Assert completion
    # ------------------------------------------------------------------ #

    document_repository.mark_ready.assert_awaited_once_with(
        persisted_document.id,
        chunk_count=len(created_chunks),
    )

    document_repository.mark_failed.assert_not_called()

    # ------------------------------------------------------------------ #
    # Assert result
    # ------------------------------------------------------------------ #

    assert result.document_id == persisted_document.id

    assert (
        result.chunk_count
        == len(created_chunks)
    )

    assert (
        result.status
        == DocumentProcessingStatus.READY
    )

# --------------------------------------------------------------------------- #
# Failure Scenarios
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_process_fails_when_parser_raises(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    document_repository: AsyncMock,
    persisted_document,
):
    """
    Processing should mark the document as FAILED when parsing fails.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.side_effect = DocumentParsingError(
        "Unable to parse 'crm.pdf'"
    )

    with pytest.raises(DocumentParsingError):
        await _create_and_process(
            service, processing_request, document_repository
        )

    document_repository.mark_processing.assert_awaited_once_with(
        persisted_document.id,
    )

    document_repository.mark_failed.assert_awaited_once()

    args = document_repository.mark_failed.await_args

    assert args.args[0] == persisted_document.id
    assert "Unable to parse" in args.kwargs["error_message"]


@pytest.mark.asyncio
async def test_process_fails_when_splitter_raises(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    persisted_document,
    parsed_document,
):
    """
    Processing should fail if text splitting fails.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.side_effect = ChunkingError(
        "Splitter failed."
    )

    with pytest.raises(ChunkingError):
        await _create_and_process(
            service, processing_request, document_repository
        )

    parser.parse.assert_called_once()

    splitter.split_text.assert_called_once()

    document_repository.mark_failed.assert_awaited_once()

    kwargs = document_repository.mark_failed.await_args.kwargs

    assert "Splitter failed" in kwargs["error_message"]


@pytest.mark.asyncio
async def test_process_fails_when_vector_store_raises(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    vector_store: AsyncMock,
    persisted_document,
    parsed_document,
    split_chunks,
    created_chunks,
):
    """
    Vector indexing failures should mark the document as FAILED.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.return_value = split_chunks

    chunk_repository.bulk_create.return_value = created_chunks

    vector_store.index_chunks.side_effect = RuntimeError(
        "Embedding service unavailable."
    )

    with pytest.raises(RuntimeError):
        await _create_and_process(
            service, processing_request, document_repository
        )

    chunk_repository.bulk_create.assert_awaited_once()

    vector_store.index_chunks.assert_awaited_once()

    document_repository.mark_ready.assert_not_called()

    document_repository.mark_failed.assert_awaited_once()

    kwargs = document_repository.mark_failed.await_args.kwargs

    assert "Embedding service unavailable" not in kwargs["error_message"]
    assert "internal error" in kwargs["error_message"].lower()


# --------------------------------------------------------------------------- #
# Additional Failure Scenarios
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_process_fails_when_chunk_repository_raises(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    persisted_document,
    parsed_document,
    split_chunks,
):
    """
    Chunk persistence failures should mark the document as FAILED.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.return_value = split_chunks

    chunk_repository.bulk_create.side_effect = RuntimeError(
        "Database write failed."
    )

    with pytest.raises(RuntimeError):
        await _create_and_process(
            service, processing_request, document_repository
        )

    chunk_repository.bulk_create.assert_awaited_once()

    document_repository.mark_ready.assert_not_called()

    document_repository.mark_failed.assert_awaited_once()

    kwargs = document_repository.mark_failed.await_args.kwargs

    assert "Database write failed" not in kwargs["error_message"]
    assert "internal error" in kwargs["error_message"].lower()


@pytest.mark.asyncio
async def test_process_handles_empty_document(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    vector_store: AsyncMock,
    persisted_document,
    parsed_document,
):
    """
    Processing an empty document should succeed with zero chunks.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.return_value = []

    chunk_repository.bulk_create.return_value = []

    result = await _create_and_process(
            service, processing_request, document_repository
        )

    vector_store.index_chunks.assert_awaited_once_with([])

    document_repository.mark_ready.assert_awaited_once_with(
        persisted_document.id,
        chunk_count=0,
    )

    assert result.chunk_count == 0

    assert (
        result.status
        == DocumentProcessingStatus.READY
    )


@pytest.mark.asyncio
async def test_process_fails_when_document_creation_fails(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    document_repository: AsyncMock,
):
    """
    Fail immediately if the document cannot be created.
    """

    document_repository.create.side_effect = RuntimeError(
        "Unable to create document."
    )

    with pytest.raises(RuntimeError):
        await _create_and_process(
            service, processing_request, document_repository
        )

    document_repository.mark_processing.assert_not_called()

    document_repository.mark_ready.assert_not_called()

    document_repository.mark_failed.assert_not_called()


@pytest.mark.asyncio
async def test_process_calls_services_in_expected_order(
    service: DocumentProcessingService,
    processing_request: DocumentProcessingRequest,
    parser: MagicMock,
    splitter: MagicMock,
    document_repository: AsyncMock,
    chunk_repository: AsyncMock,
    vector_store: AsyncMock,
    persisted_document,
    parsed_document,
    split_chunks,
    created_chunks,
):
    """
    Verify the complete processing workflow is executed.
    """

    document_repository.create.return_value = persisted_document

    parser.parse.return_value = parsed_document

    splitter.split_text.return_value = split_chunks

    chunk_repository.bulk_create.return_value = created_chunks

    await _create_and_process(
            service, processing_request, document_repository
        )

    document_repository.create.assert_awaited_once()

    document_repository.mark_processing.assert_awaited_once()

    parser.parse.assert_called_once()

    splitter.split_text.assert_called_once()

    chunk_repository.bulk_create.assert_awaited_once()

    vector_store.index_chunks.assert_awaited_once()

    document_repository.mark_ready.assert_awaited_once()

    document_repository.mark_failed.assert_not_called()
    
