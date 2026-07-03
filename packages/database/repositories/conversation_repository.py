from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.repositories.base_repository import BaseRepository
from packages.database.models.conversation import Conversation
from datetime import datetime, UTC

class ConversationRepository(BaseRepository):
    """Repository for the ``Conversation`` model."""

    model = Conversation

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Retrieve a conversation by its ID, ensuring it belongs to the current tenant
        and is not soft-deleted.
        """
        stmt = (
            select(self.model)
            .where(self.model.id == conversation_id)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, conversation_id: UUID, **data: Any) -> Optional[Conversation]:
        """
        Update a conversation. Only ``title`` and ``status`` may be modified.
        Ownership is enforced – the tenant_id cannot be changed.
        """
        instance = await self.get_by_id(conversation_id)
        if instance is None:
            return None

        allowed_fields = {"title", "status", "updated_at"}

        for field in list(data.keys()):
            if field not in allowed_fields:
                data.pop(field)

        for field, value in data.items():
            setattr(instance, field, value)

        await self.session.flush()
        await self.session.refresh(instance)

        return instance

    async def soft_delete(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Soft‑delete a conversation by setting ``deleted_at`` to the current
        UTC timestamp (using ``func.now()``). Returns the updated instance
        (or ``None`` if not found).
        """
        instance = await self.get_by_id(conversation_id)
        if instance is None:
            return None

        instance.deleted_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def list_for_user(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        List conversations belonging to the given ``user_id`` (and tenant),
        excluding soft‑deleted rows.

        Results are ordered by ``created_at`` descending, with pagination
        applied via ``limit``/``offset``.
        """
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.user_id == user_id)
            .where(self.model.deleted_at.is_(None))
        )

        if status:
            stmt = stmt.where(self.model.status == status)

        stmt = (
            stmt.order_by(desc(self.model.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()