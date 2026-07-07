"""Document processing service."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.file_processing.chunkers.base import TextChunker
from app.file_processing.embeddings.base import EmbeddingProvider
from app.file_processing.parsers.factory import ParserFactory

from packages.database.models.enums import DocumentProcessingStatus
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)


class DocumentProcessingService:
    """Coordinates document parsing, chunking and embedding."""

    def __init__(
        self,
        knowledge_repo: KnowledgeDocumentRepository,
        chunk_repo: DocumentChunkRepository,
        parser_factory: ParserFactory,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.knowledge_repo = knowledge_repo
        self.chunk_repo = chunk_repo
        self.parser_factory = parser_factory
        self.chunker = chunker
        self.embedding_provider = embedding_provider

    async def process_document(
        self,
        file_path: Path,
        tenant_id: UUID,
    ):
        """
        Parse, chunk and embed a document.
        """

        document = await self.knowledge_repo.create(
            tenant_id=tenant_id,
            filename=file_path.name,
            storage_path=str(file_path),
            processing_status=DocumentProcessingStatus.UPLOADED,
        )

        try:
            parser = self.parser_factory.get_parser(file_path)

            await self.knowledge_repo.update_status(
                document.id,
                DocumentProcessingStatus.PARSING,
            )

            extracted_document = parser.parse(file_path)

            if not extracted_document.text.strip():
                raise ValueError("Document contains no text.")

            await self.knowledge_repo.update_status(
                document.id,
                DocumentProcessingStatus.CHUNKING,
            )

            chunks = self.chunker.chunk(extracted_document)

            await self.knowledge_repo.update_status(
                document.id,
                DocumentProcessingStatus.EMBEDDING,
            )

            embeddings = await self.embedding_provider.embed_texts(
                [chunk.text for chunk in chunks]
            )

            chunk_records = []

            for chunk, embedding in zip(chunks, embeddings):
                chunk_records.append(
                    {
                        "document_id": document.id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.text,
                        "token_count": chunk.token_count,
                        "embedding": embedding.embedding,
                        "chunk_metadata": chunk.metadata,
                    }
                )

            await self.chunk_repo.bulk_create(chunk_records)

            await self.knowledge_repo.update_status(
                document.id,
                DocumentProcessingStatus.READY,
            )

            return document

        except Exception:
            await self.knowledge_repo.update_status(
                document.id,
                DocumentProcessingStatus.FAILED,
            )
            raise

    async def reprocess_document(
        self,
        document_id: UUID,
    ):
        """
        Reprocess an existing document.
        """

        document = await self.knowledge_repo.get_with_chunks(
            document_id
        )

        if document is None:
            raise ValueError("Document not found.")

        await self.chunk_repo.delete_by_document_id(
            document.id
        )

        return await self.process_document(
            Path(document.storage_path),
            document.tenant_id,
        )

    async def mark_failed(
        self,
        document_id: UUID,
        message: str | None = None,
    ) -> None:
        """
        Mark a document as failed.
        """

        if hasattr(self.knowledge_repo, "update_processing_info"):
            await self.knowledge_repo.update_processing_info(
                document_id,
                error_message=message,
            )

        await self.knowledge_repo.update_status(
            document_id,
            DocumentProcessingStatus.FAILED,
        )