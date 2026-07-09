"""Service layer for RetrievalTrace."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from packages.database.models.retrieval_trace import RetrievalTrace
from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)


class RetrievalTraceService:
    """Service for retrieval trace operations."""

    def __init__(
        self,
        repository: RetrievalTraceRepository,
    ) -> None:
        self.repository = repository

    async def create_trace(
        self,
        **data: Any,
    ) -> RetrievalTrace:
        """Create a retrieval trace."""
        return await self.repository.create(**data)

    async def get_trace(
        self,
        trace_id: UUID,
    ) -> RetrievalTrace | None:
        """Retrieve a trace by ID."""
        return await self.repository.get_by_id(trace_id)

    async def get_trace_with_chunks(
        self,
        trace_id: UUID,
    ) -> RetrievalTrace | None:
        """Retrieve a trace together with retrieved chunks."""
        return await self.repository.get_with_chunks(trace_id)

    async def list_by_conversation(
        self,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RetrievalTrace]:
        """List retrieval traces for a conversation."""
        return await self.repository.list_by_conversation(
            conversation_id,
            limit=limit,
            offset=offset,
        )

    async def list_by_tenant(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RetrievalTrace]:
        """List retrieval traces for the tenant."""
        return await self.repository.list_by_tenant(
            limit=limit,
            offset=offset,
        )

    async def update_trace(
        self,
        trace_id: UUID,
        **data: Any,
    ) -> RetrievalTrace | None:
        """Update a retrieval trace."""
        return await self.repository.update(
            trace_id,
            **data,
        )

    async def update_status(
        self,
        trace_id: UUID,
        status: str,
        error_message: str | None = None,
    ) -> RetrievalTrace | None:
        """Update retrieval status."""
        return await self.repository.update_status(
            trace_id,
            status=status,
            error_message=error_message,
        )

    async def delete_trace(
        self,
        trace_id: UUID,
    ) -> bool:
        """Delete a retrieval trace."""
        return await self.repository.delete(trace_id)