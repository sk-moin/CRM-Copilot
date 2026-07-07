"""Repository for DocumentChunk model with tenant isolation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.document_chunk import DocumentChunk
from packages.database.repositories.base_repository import BaseRepository


class DocumentChunkRepository(BaseRepository):
    """Repository for DocumentChunk entities."""

    model = DocumentChunk

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, tenant_id)

    async def get_by_document_id(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        """Return all chunks belonging to a document."""
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

    async def delete_by_document_id(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all chunks belonging to a document."""
        await self.session.execute(
            DocumentChunk.__table__.delete().where(
                DocumentChunk.tenant_id == self.tenant_id,
                DocumentChunk.document_id == document_id,
            )
        )
        await self.session.flush()

    async def bulk_create(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """Create multiple chunks in a single database operation."""
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

    async def similarity_search(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
    ) -> list[DocumentChunk]:
        """Return chunks ordered by cosine similarity."""
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .order_by(self.model.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_by_metadata(
        self,
        filters: dict[str, Any],
    ) -> list[DocumentChunk]:
        """Filter chunks by metadata values."""
        conditions = []

        for key, value in filters.items():
            conditions.append(
                self.model.chunk_metadata[key].as_string() == str(value)
            )

        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            and_(*conditions),
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()