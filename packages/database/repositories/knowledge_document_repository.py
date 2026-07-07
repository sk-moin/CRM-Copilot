"""Repository for KnowledgeDocument model with tenant isolation."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.database.models.enums import DocumentProcessingStatus
from packages.database.models.knowledge_document import KnowledgeDocument
from packages.database.repositories.base_repository import BaseRepository


class KnowledgeDocumentRepository(BaseRepository):
    """Repository for knowledge documents with tenant isolation."""

    model = KnowledgeDocument

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, tenant_id)

    async def list_by_status(
        self,
        status: DocumentProcessingStatus,
    ) -> List[KnowledgeDocument]:
        """List documents by processing status."""
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.processing_status == status)
            .order_by(self.model.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_document_type(
        self,
        document_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KnowledgeDocument]:
        """List documents by document type."""
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.document_type == document_type)
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
        """Load a document together with all chunks."""
        stmt = (
            select(self.model)
            .options(selectinload(self.model.chunks))
            .where(self.model.id == document_id)
            .where(self.model.tenant_id == self.tenant_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentProcessingStatus,
    ) -> Optional[KnowledgeDocument]:
        """Update only processing status."""
        instance = await self.get_by_id(document_id)

        if instance is None:
            return None

        instance.processing_status = status

        await self.session.flush()
        await self.session.refresh(instance)

        return instance

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
        """Update processing metadata for a document."""
        instance = await self.get_by_id(document_id)

        if instance is None:
            return None

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