"""Repository for KnowledgeDocument model with tenant isolation."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.database.models.enums import DocumentProcessingStatus
from packages.database.models.knowledge_document import KnowledgeDocument
from packages.database.repositories.base_repository import BaseRepository


class KnowledgeDocumentRepository(BaseRepository):
    """Repository for KnowledgeDocument entities."""

    model = KnowledgeDocument

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        super().__init__(session, tenant_id)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    async def list_by_status(
        self,
        status: DocumentProcessingStatus,
    ) -> List[KnowledgeDocument]:
        """Return documents with the given processing status."""

        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.processing_status == status,
            )
            .order_by(self.model.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_document_type(
        self,
        document_type: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeDocument]:
        """Return documents of a specific type."""

        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.document_type == document_type,
            )
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_chunks(
        self,
        document_id: UUID,
    ) -> Optional[KnowledgeDocument]:
        """Return a document together with all chunks."""

        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.chunks),
            )
            .where(
                self.model.id == document_id,
                self.model.tenant_id == self.tenant_id,
            )
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Status Updates
    # ------------------------------------------------------------------ #

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentProcessingStatus,
    ) -> Optional[KnowledgeDocument]:
        """Update only the processing status."""

        return await self.update_processing_result(
            document_id=document_id,
            status=status,
        )

    async def mark_processing(
        self,
        document_id: UUID,
    ) -> Optional[KnowledgeDocument]:
        """Mark a document as currently processing."""

        return await self.update_processing_result(
            document_id=document_id,
            status=DocumentProcessingStatus.PROCESSING,
            processing_started_at=datetime.utcnow(),
        )

    async def mark_completed(
        self,
        document_id: UUID,
        *,
        chunk_count: int,
    ) -> Optional[KnowledgeDocument]:
        """Mark processing as completed."""

        return await self.update_processing_result(
            document_id=document_id,
            status=DocumentProcessingStatus.COMPLETED,
            chunk_count=chunk_count,
            processed_at=datetime.utcnow(),
            error_message=None,
        )

    async def mark_failed(
        self,
        document_id: UUID,
        *,
        error_message: str,
    ) -> Optional[KnowledgeDocument]:
        """Mark processing as failed."""

        return await self.update_processing_result(
            document_id=document_id,
            status=DocumentProcessingStatus.FAILED,
            processed_at=datetime.utcnow(),
            error_message=error_message,
        )

    async def update_processing_result(
        self,
        *,
        document_id: UUID,
        status: DocumentProcessingStatus | None = None,
        chunk_count: int | None = None,
        storage_path: str | None = None,
        error_message: str | None = None,
        processing_started_at: datetime | None = None,
        processed_at: datetime | None = None,
    ) -> Optional[KnowledgeDocument]:
        """
        Update processing-related fields in a single database operation.
        """

        instance = await self.get_by_id(document_id)

        if instance is None:
            return None

        if status is not None:
            instance.processing_status = status

        if chunk_count is not None:
            instance.chunk_count = chunk_count

        if storage_path is not None:
            instance.storage_path = storage_path

        if error_message is not None:
            instance.error_message = error_message

        if processing_started_at is not None:
            instance.processing_started_at = processing_started_at

        if processed_at is not None:
            instance.processed_at = processed_at

        await self.session.flush()
        await self.session.refresh(instance)

        return instance

    # ------------------------------------------------------------------ #
    # Generic Metadata Updates
    # ------------------------------------------------------------------ #

    async def update_processing_info(
        self,
        document_id: UUID,
        *,
        chunk_count: int | None = None,
        storage_path: str | None = None,
        error_message: str | None = None,
        processing_started_at: datetime | None = None,
        processed_at: datetime | None = None,
    ) -> Optional[KnowledgeDocument]:
        """
        Backwards-compatible wrapper.

        Prefer update_processing_result() for new code.
        """

        return await self.update_processing_result(
            document_id=document_id,
            chunk_count=chunk_count,
            storage_path=storage_path,
            error_message=error_message,
            processing_started_at=processing_started_at,
            processed_at=processed_at,
        )