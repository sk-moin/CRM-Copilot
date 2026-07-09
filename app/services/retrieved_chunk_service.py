"""Service layer for RetrievedChunk."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from packages.database.models.retrieved_chunk import RetrievedChunk
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)


class RetrievedChunkService:
    """Service for retrieved chunk operations."""

    def __init__(
        self,
        repository: RetrievedChunkRepository,
    ) -> None:
        self.repository = repository

    async def create_chunk(
        self,
        **data: Any,
    ) -> RetrievedChunk:
        """Create a retrieved chunk."""
        return await self.repository.create(**data)

    async def bulk_create(
        self,
        chunks_data: list[dict[str, Any]],
    ) -> list[RetrievedChunk]:
        """Create multiple retrieved chunks."""
        return await self.repository.bulk_create(chunks_data)

    async def get_chunk(
        self,
        chunk_id: UUID,
    ) -> RetrievedChunk | None:
        """Retrieve a retrieved chunk."""
        return await self.repository.get_by_id(chunk_id)

    async def get_by_trace(
        self,
        trace_id: UUID,
    ) -> list[RetrievedChunk]:
        """Retrieve chunks for a retrieval trace."""
        return await self.repository.get_by_trace(trace_id)

    async def delete_by_trace(
        self,
        trace_id: UUID,
    ) -> int:
        """Delete all chunks belonging to a trace."""
        return await self.repository.delete_by_trace(trace_id)

    async def delete_chunk(
        self,
        chunk_id: UUID,
    ) -> bool:
        """Delete a retrieved chunk."""
        return await self.repository.delete(chunk_id)