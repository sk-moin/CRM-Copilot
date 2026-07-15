"""
app/rag/vectorstores/pgvector_store.py

Tenant-aware PGVector store for the CRM Copilot RAG pipeline.

Responsibilities
----------------
- Generate embeddings
- Persist embeddings through the repository
- Perform similarity search
- Convert database models into LangChain Documents
"""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from langchain_core.documents import Document

from app.rag.embeddings.embedding_provider import EmbeddingProvider
from app.rag.exceptions import VectorStoreError
from packages.database.models.document_chunk import DocumentChunk
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)



class PGVectorStore:
    """High-level vector store built on DocumentChunkRepository."""

    def __init__(
        self,
        *,
        repository: DocumentChunkRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider

    # ------------------------------------------------------------------ #
    # Indexing
    # ------------------------------------------------------------------ #

    async def index_chunks(
        self,
        chunks: Iterable[DocumentChunk],
    ) -> None:
        """
        Generate embeddings and persist them.
        """

        chunks = list(chunks)

        if not chunks:
            return

        try:
            embeddings = await self.embedding_provider.embed_documents(
                [chunk.content for chunk in chunks]
            )

            if len(embeddings) != len(chunks):
                raise VectorStoreError(
                    "Embedding count does not match chunk count."
                )

            await self.repository.update_embeddings(
                chunks,
                embeddings,
            )

        except VectorStoreError:
            raise

        except Exception as exc:
            raise VectorStoreError(
                "Failed to index document chunks."
            ) from exc

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    async def similarity_search(
        self,
        *,
        query: str,
        k: int = 5,
        document_id: UUID | None = None,
    ) -> list[Document]:
        """
        Return LangChain Documents.
        """

        if not query.strip():
            raise VectorStoreError(
                "Query cannot be empty."
            )

        try:
            embedding = await self.embedding_provider.embed_query(
                query
            )

            chunks = await self.repository.similarity_search(
                embedding,
                limit=k,
                document_id=document_id,
            )

            return [
                self._to_document(chunk)
                for chunk in chunks
            ]

        except VectorStoreError:
            raise

        except Exception as exc:
            raise VectorStoreError(
                "Similarity search failed."
            ) from exc

    # ------------------------------------------------------------------ #
    # Search With Scores
    # ------------------------------------------------------------------ #

    async def similarity_search_with_scores(
        self,
        *,
        query: str,
        k: int = 5,
        document_id: UUID | None = None,
    ) -> list[tuple[Document, float]]:
        """
        Return Documents together with similarity scores.

        Repository currently does not expose scores, therefore this
        method returns a default similarity score of 1.0 until
        repository support is added.
        """

        embedding = await self.embedding_provider.embed_query(query)

        results = await self.repository.similarity_search_with_scores(
            embedding=embedding,
            limit=k,
            document_id=document_id,
        )

        return [
            (self._to_document(chunk), score)
            for chunk, score in results
        ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_document(
        chunk: DocumentChunk,
    ) -> Document:
        """
        Convert ORM model to LangChain Document.
        """

        metadata = {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "tenant_id": str(chunk.tenant_id),
            "chunk_index": chunk.chunk_index,
            "token_count": chunk.token_count,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }

        if chunk.chunk_metadata:
            metadata.update(chunk.chunk_metadata)

        if getattr(chunk, "document", None):
            metadata.update(
                {
                    "title": chunk.document.title,
                    "filename": chunk.document.filename,
                    "mime_type": chunk.document.mime_type,
                    "source_type": chunk.document.source_type,
                }
            )

        return Document(
            page_content=chunk.content,
            metadata=metadata,
        )