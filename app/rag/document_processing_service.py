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

        try:
            await self.document_repository.mark_processing(
                document.id,
            )

            parsed = self.parser.parse(
                request.storage_path,
            )

            split_chunks = self.splitter.split_text(
                parsed.content,
                metadata={
                    "document_id": str(document.id),
                    "filename": request.filename,
                    "title": request.title,
                    "document_type": request.document_type,
                },
            )

            chunk_payload: list[dict] = []

            for index, chunk in enumerate(split_chunks):
                start_char = chunk.metadata.get("start_index", 0)

                chunk_payload.append(
                    {
                        "document_id": document.id,
                        "content": chunk.page_content,
                        "chunk_index": index,
                        "start_char": start_char,
                        "end_char": start_char + len(chunk.page_content),
                        "token_count": len(chunk.page_content.split()),
                        "chunk_metadata": chunk.metadata,
                    }
                )

            created_chunks = await self.chunk_repository.bulk_create(
                chunk_payload,
            )

            await self.vector_store.index_chunks(
                created_chunks,
            )

            await self.document_repository.mark_ready(
                document.id,
                chunk_count=len(created_chunks),
            )

            await self.document_repository.session.commit()

            return DocumentProcessingResult(
                document_id=document.id,
                chunk_count=len(created_chunks),
                status=DocumentProcessingStatus.READY,
            )

        except Exception as exc:

            await self.document_repository.mark_failed(
                document.id,
                error_message=str(exc),
            )

            raise