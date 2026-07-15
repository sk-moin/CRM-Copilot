"""Repository for DocumentChunk model with tenant isolation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.document_chunk import DocumentChunk
from packages.database.repositories.base_repository import BaseRepository


class DocumentChunkRepository(BaseRepository):
    """Repository for DocumentChunk entities."""

    model = DocumentChunk

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        super().__init__(session, tenant_id)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    async def get_by_document_id(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        """
        Return all chunks belonging to a document.
        """

        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.document_id == document_id,
            )
            .order_by(self.model.chunk_index.asc())
        )

        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def count_by_document(
        self,
        document_id: UUID,
    ) -> int:
        """
        Return number of chunks for a document.
        """

        stmt = (
            select(func.count(self.model.id))
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.document_id == document_id,
            )
        )

        result = await self.session.execute(stmt)

        return result.scalar_one()

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #

    async def bulk_create(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """
        Create multiple chunks in one database operation.
        """

        instances = [
            DocumentChunk(
                tenant_id=self.tenant_id,
                **chunk,
            )
            for chunk in chunks
        ]

        self.session.add_all(instances)

        await self.session.flush()

        for instance in instances:
            await self.session.refresh(instance)

        return instances

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    async def delete_by_document_id(
        self,
        document_id: UUID,
    ) -> None:
        """
        Delete every chunk belonging to a document.
        """

        stmt = (
            delete(DocumentChunk)
            .where(
                DocumentChunk.tenant_id == self.tenant_id,
                DocumentChunk.document_id == document_id,
            )
        )

        await self.session.execute(stmt)
        await self.session.flush()

    # ------------------------------------------------------------------ #
    # Embeddings
    # ------------------------------------------------------------------ #

    async def update_embeddings(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Persist generated embeddings.
        """

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        await self.session.flush()

    # ------------------------------------------------------------------ #
    # Vector Search
    # ------------------------------------------------------------------ #

    async def similarity_search(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        document_id: UUID | None = None,
    ) -> list[DocumentChunk]:
        """
        Return chunks ordered by cosine similarity.
        """

        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
            )
        )

        if document_id is not None:
            stmt = stmt.where(
                self.model.document_id == document_id,
            )

        stmt = (
            stmt.order_by(
                self.model.embedding.cosine_distance(
                    embedding,
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)

        return result.scalars().all()
    

    async def similarity_search_with_scores(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        document_id: UUID | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Return chunks together with cosine similarity scores.
        """

        distance = self.model.embedding.cosine_distance(
            embedding
        ).label("distance")

        stmt = (
            select(
                self.model,
                distance,
            )
            .where(
                self.model.tenant_id == self.tenant_id,
            )
        )

        if document_id is not None:
            stmt = stmt.where(
                self.model.document_id == document_id,
            )

        stmt = stmt.order_by(distance).limit(limit)

        result = await self.session.execute(stmt)

        rows = result.all()

        return [
            (
                chunk,
                max(0.0, 1.0 - float(distance)),
            )
            for chunk, distance in rows
        ]

    # ------------------------------------------------------------------ #
    # Metadata
    # ------------------------------------------------------------------ #

    async def filter_by_metadata(
        self,
        filters: dict[str, Any],
    ) -> list[DocumentChunk]:
        """
        Filter chunks using JSON metadata.
        """

        conditions = []

        for key, value in filters.items():
            conditions.append(
                self.model.chunk_metadata[key].as_string()
                == str(value)
            )

        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                and_(*conditions),
            )
            .order_by(
                self.model.chunk_index.asc(),
            )
        )

        result = await self.session.execute(stmt)

        return result.scalars().all()