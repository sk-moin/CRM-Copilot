"""Repository for RetrievalTrace model with tenant isolation."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.database.models.retrieval_trace import RetrievalTrace
from packages.database.repositories.base_repository import BaseRepository


class RetrievalTraceRepository(BaseRepository):
    """Repository for retrieval traces with tenant isolation."""

    model = RetrievalTrace

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, tenant_id)

    async def list_by_conversation(
        self,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RetrievalTrace]:
        """List retrieval traces for a conversation."""

        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.conversation_id == conversation_id)
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RetrievalTrace]:
        """List retrieval traces by status."""

        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.status == status)
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_chunks(
        self,
        trace_id: UUID,
    ) -> Optional[RetrievalTrace]:
        """Load a retrieval trace together with all retrieved chunks."""

        stmt = (
            select(self.model)
            .options(selectinload(self.model.retrieved_chunk_records))
            .where(self.model.id == trace_id)
            .where(self.model.tenant_id == self.tenant_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        trace_id: UUID,
        *,
        status: str,
        error_message: str | None = None,
    ) -> Optional[RetrievalTrace]:
        """Update retrieval status and optional error message."""

        instance = await self.get_by_id(trace_id)

        if instance is None:
            return None

        instance.status = status
        instance.error_message = error_message

        await self.session.flush()
        await self.session.refresh(instance)

        return instance

    async def update_metrics(
        self,
        trace_id: UUID,
        *,
        embedding_latency_ms: float | None = None,
        retrieval_latency_ms: float | None = None,
        total_latency_ms: float | None = None,
        embedding_model: str | None = None,
        vector_store: str | None = None,
        retrieved_chunk: int | None = None,
        retrieval_metadata: dict | None = None,
    ) -> Optional[RetrievalTrace]:
        """Update retrieval performance metrics."""

        instance = await self.get_by_id(trace_id)

        if instance is None:
            return None

        if embedding_latency_ms is not None:
            instance.embedding_latency_ms = embedding_latency_ms

        if retrieval_latency_ms is not None:
            instance.retrieval_latency_ms = retrieval_latency_ms

        if total_latency_ms is not None:
            instance.total_latency_ms = total_latency_ms

        if embedding_model is not None:
            instance.embedding_model = embedding_model

        if vector_store is not None:
            instance.vector_store = vector_store

        if retrieved_chunk is not None:
            instance.retrieved_chunk = retrieved_chunk

        if retrieval_metadata is not None:
            instance.retrieval_metadata = retrieval_metadata

        await self.session.flush()
        await self.session.refresh(instance)

        return instance
