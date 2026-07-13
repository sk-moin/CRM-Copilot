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

from datetime import datetime

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

    async def process(
        self,
        request: DocumentProcessingRequest,
    ) -> DocumentProcessingResult:
        """
        Parse, chunk, embed and index a document.
        """

        document = await self.document_repository.create(
            tenant_id=request.tenant_id,
            org_id=request.organization_id,
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

        try:
            await self.document_repository.mark_processing(
                document.id,
            )

            parsed = self.parser.parse(
                request.storage_path,
            )

            split_chunks = self.splitter.split(
                parsed.content,
                metadata={
                    "document_id": str(document.id),
                    "filename": request.filename,
                    "title": request.title,
                    "document_type": request.document_type,
                },
            )

            chunk_payload = []

            for chunk in split_chunks:
                chunk_payload.append(
                    {
                        "document_id": document.id,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "chunk_metadata": chunk.metadata,
                    }
                )

            created_chunks = await self.chunk_repository.bulk_create(
                chunk_payload,
            )

            await self.vector_store.index_chunks(
                created_chunks,
            )

            await self.document_repository.mark_completed(
                document.id,
                chunk_count=len(created_chunks),
            )

            return DocumentProcessingResult(
                document_id=document.id,
                chunk_count=len(created_chunks),
                status=DocumentProcessingStatus.COMPLETED,
            )

        except Exception as exc:

            await self.document_repository.mark_failed(
                document.id,
                error_message=str(exc),
            )

            raise