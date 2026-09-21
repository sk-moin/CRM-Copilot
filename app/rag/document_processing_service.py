"""
app/rag/document_processing_service.py

Service responsible for ingesting documents into the RAG pipeline.

Workflow

File
    │
    ▼
Parser
    │
    ▼
Text Splitter
    │
    ▼
Create Document Chunks
    │
    ▼
Generate Embeddings
    │
    ▼
Index into PGVector
    │
    ▼
Mark Processing Complete
"""

from __future__ import annotations

import logging

from datetime import datetime

from app.rag.exceptions import (
    ChunkingError,
    DocumentParsingError,
    DocumentNotFoundError,
    DocumentProcessingError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from app.rag.loaders.parser import DocumentParser
from app.rag.models.document_processing_request import (
    DocumentProcessingRequest,
)
from app.rag.models.document_processing_result import (
    DocumentProcessingResult,
)
from app.rag.splitters.text_splitter import TextSplitter
from app.rag.vectorstores.pgvector_store import PGVectorStore

from packages.database.models.enums import (
    DocumentProcessingStatus,
)
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)


# Exceptions this pipeline raises deliberately, with messages written to be
# read by whoever uploaded the document. Everything else -- asyncpg,
# SQLAlchemy, an embedding provider's HTTP payload -- can carry server paths,
# SQL, or credentials in its text, and `error_message` is served verbatim by
# GET /documents/{id}/status.
_USER_FACING_ERRORS = (
    UnsupportedDocumentTypeError,
    DocumentParsingError,
    EmptyDocumentError,
    ChunkingError,
)


def _user_facing_error(exc: Exception) -> str:
    """The failure reason to store on the document.

    Muting every message is its own bug -- the project has done it before and
    left users polling a FAILED document with no clue what to change. So the
    known causes keep their text, and only the unexpected ones collapse. The
    full exception is logged either way.
    """

    if isinstance(exc, _USER_FACING_ERRORS):
        return str(exc)[:2000]

    return (
        "Processing failed because of an internal error. "
        "The document was not indexed; contact support if it persists."
    )


logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Handles document ingestion into the RAG knowledge base.
    """

    def __init__(
        self,
        *,
        parser: DocumentParser,
        splitter: TextSplitter,
        document_repository: KnowledgeDocumentRepository,
        chunk_repository: DocumentChunkRepository,
        vector_store: PGVectorStore,
    ) -> None:
        self.parser = parser
        self.splitter = splitter
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.vector_store = vector_store

    async def create_document(
        self,
        request: DocumentProcessingRequest,
    ):
        """Persist the document row and commit it, without processing.

        Split out so an upload can return an id immediately and hand the work
        to a background job. The commit matters: the worker is a different
        process and cannot see an uncommitted row.
        """

        document = await self.document_repository.create(
            tenant_id=request.tenant_id,
            org_id=request.org_id,
            owner_id=request.owner_id,
            title=request.title,
            filename=request.filename,
            storage_path=request.storage_path,
            document_type=request.document_type,
            source_type=request.source_type,
            mime_type=request.mime_type,
            file_size=request.file_size,
            processing_status=DocumentProcessingStatus.UPLOADED,
        )

        await self.document_repository.session.commit()

        return document

    async def record_failure(self, document_id, exc: Exception) -> None:
        """Mark a document FAILED after the caller decided not to retry.

        Rolls back first, and must: `process_document` only rolls back from
        its own `except Exception`, and a deadline expiring cancels the task
        instead, so `CancelledError` -- a BaseException -- goes straight past
        that handler and only becomes `TimeoutError` further out. Arriving
        here on an un-rolled-back session then either committed the half-done
        ingestion alongside the FAILED status (chunks with no embeddings,
        which retrieval would still return) or raised PendingRollbackError
        and left the document at PARSING with nothing recorded.

        Rollback is idempotent on a clean session, so this is safe for the
        ordinary path too.
        """

        await self.document_repository.session.rollback()

        await self._write_failure(document_id, exc)

    async def _write_failure(self, document_id, exc: Exception) -> None:
        await self.document_repository.mark_failed(
            document_id,
            error_message=_user_facing_error(exc),
        )
        await self.document_repository.session.commit()

    async def process_document(
        self,
        document_id,
        *,
        record_failure: bool = True,
    ) -> DocumentProcessingResult:
        """Parse, chunk, embed and index an already-persisted document.

        `record_failure=False` lets a caller that intends to retry leave the
        status alone, so a transient failure does not flash FAILED at anyone
        polling between attempts.
        """

        document = await self.document_repository.get_by_id(document_id)

        if document is None:
            raise DocumentNotFoundError(
                f"Document {document_id} not found."
            )

        # Read once, up front. `session.rollback()` in the failure path
        # expires every loaded instance, so touching `document.id` after it
        # triggers a lazy refresh from sync attribute access -- SQLAlchemy
        # raises MissingGreenlet, which replaces the real error and leaves
        # the document with no FAILED status at all.
        document_pk = document.id

        try:
            await self.document_repository.mark_processing(document_pk)

            # Committed so the PARSING state is visible to the API process
            # while the work is still running. Without this the whole job is
            # invisible until it finishes, which is the point of the feature.
            await self.document_repository.session.commit()

            parsed = self.parser.parse(document.storage_path)

            split_chunks = self.splitter.split_text(
                parsed.content,
                metadata={
                    "document_id": str(document_pk),
                    "filename": document.filename,
                    "title": document.title,
                    "document_type": document.document_type,
                },
            )

            chunk_payload: list[dict] = []

            for index, chunk in enumerate(split_chunks):
                start_char = chunk.metadata.get("start_index", 0)

                chunk_payload.append(
                    {
                        "document_id": document_pk,
                        "content": chunk.page_content,
                        "chunk_index": index,
                        "start_char": start_char,
                        "end_char": start_char + len(chunk.page_content),
                        "token_count": len(chunk.page_content.split()),
                        "chunk_metadata": chunk.metadata,
                    }
                )

            # Idempotent: a retry, or a worker killed mid-embed, must not
            # leave two sets of chunks behind.
            await self.chunk_repository.delete_by_document_id(document_pk)

            created_chunks = await self.chunk_repository.bulk_create(
                chunk_payload,
            )

            await self.vector_store.index_chunks(created_chunks)

            await self.document_repository.mark_ready(
                document_pk,
                chunk_count=len(created_chunks),
            )

            await self.document_repository.session.commit()

            return DocumentProcessingResult(
                document_id=document_pk,
                chunk_count=len(created_chunks),
                status=DocumentProcessingStatus.READY,
            )

        except Exception as exc:
            # Roll back the failed work before recording the failure.
            # Previously mark_failed was called on an aborted transaction and
            # then re-raised without committing, so the caller's rollback
            # discarded the FAILED status and the document was stuck looking
            # like it was still parsing.
            logger.exception(
                "rag.document_processing.failed",
                extra={"document_id": str(document_pk)},
            )

            await self.document_repository.session.rollback()

            if record_failure:
                await self._write_failure(document_pk, exc)

            raise
