"""Repository for RetrievedChunk model with tenant isolation."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.database.models.retrieved_chunk import RetrievedChunk
from packages.database.repositories.base_repository import BaseRepository


class RetrievedChunkRepository(BaseRepository):
    """Repository for retrieved chunks with tenant isolation."""

    model = RetrievedChunk

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, tenant_id)

    async def get_by_trace(
        self,
        trace_id: UUID,
    ) -> List[RetrievedChunk]:
        """Return all retrieved chunks for a retrieval trace."""

        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.trace),
                selectinload(self.model.document),
                selectinload(self.model.chunk),
            )
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.trace_id == trace_id)
            .order_by(self.model.rank.asc())
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def bulk_create(
        self,
        chunks: List[dict[str, Any]],
    ) -> List[RetrievedChunk]:
        """Create multiple retrieved chunks in a single transaction."""

        instances = [
            self.model(
                tenant_id=self.tenant_id,
                **chunk_data,
            )
            for chunk_data in chunks
        ]

        self.session.add_all(instances)
        await self.session.flush()

        for instance in instances:
            await self.session.refresh(instance)

        return instances

    async def delete_by_trace(
        self,
        trace_id: UUID,
    ) -> int:
        """Delete all retrieved chunks for a retrieval trace."""

        stmt = (
            delete(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.trace_id == trace_id)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount or 0

    async def list_by_document(
        self,
        document_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RetrievedChunk]:
        """List retrieved chunks for a knowledge document."""

        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.document_id == document_id)
            .order_by(self.model.rank.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()
