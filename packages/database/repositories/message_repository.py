from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.repositories.base_repository import BaseRepository
from packages.database.models.message import Message
from packages.database.models.conversation import Conversation


class MessageRepository(BaseRepository):
    """
    Repository for immutable chat messages.

    Rules:
    - Tenant scoped.
    - Messages are immutable (no update/delete).
    - History ordered by created_at ASC.
    - Messages belonging to soft-deleted conversations are hidden.
    """

    model = Message

    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """
        Retrieve a message by ID within the current tenant.

        Messages whose parent conversation has been soft-deleted are excluded.
        """
        stmt = (
            select(self.model)
            .join(
                Conversation,
                Conversation.id == self.model.conversation_id,
            )
            .where(self.model.id == message_id)
            .where(self.model.tenant_id == self.tenant_id)
            .where(Conversation.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_conversation(
        self,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """
        Return ordered message history for a conversation.

        Results:
        - Tenant scoped
        - Excludes soft-deleted conversations
        - Ordered oldest → newest
        - Supports pagination
        """
        stmt = (
            select(self.model)
            .join(
                Conversation,
                Conversation.id == self.model.conversation_id,
            )
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.conversation_id == conversation_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(self.model.created_at.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()
