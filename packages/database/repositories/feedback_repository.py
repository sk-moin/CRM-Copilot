from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.repositories.base_repository import BaseRepository
from packages.database.models.feedback import MessageFeedback
from packages.database.models.message import Message
from packages.database.models.conversation import Conversation


class FeedbackRepository(BaseRepository):
    """
    Repository for message feedback.

    Rules:
    - Tenant scoped.
    - One feedback per message (enforced by DB unique constraint).
    - Read operations exclude messages belonging to soft-deleted conversations.
    """

    model = MessageFeedback

    async def get_by_message(
        self,
        message_id: UUID,
    ) -> Optional[MessageFeedback]:
        """
        Retrieve feedback for a specific message.

        Returns None if:
        - feedback does not exist
        - message belongs to another tenant
        - parent conversation has been soft deleted
        """
        stmt = (
            select(self.model)
            .join(
                Message,
                Message.id == self.model.message_id,
            )
            .join(
                Conversation,
                Conversation.id == Message.conversation_id,
            )
            .where(self.model.tenant_id == self.tenant_id)
            .where(self.model.message_id == message_id)
            .where(Conversation.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_conversation(
        self,
        conversation_id: UUID,
    ) -> List[MessageFeedback]:
        """
        Return all feedback associated with a conversation.

        Results are tenant scoped and exclude soft-deleted conversations.
        """
        stmt = (
            select(self.model)
            .join(
                Message,
                Message.id == self.model.message_id,
            )
            .join(
                Conversation,
                Conversation.id == Message.conversation_id,
            )
            .where(self.model.tenant_id == self.tenant_id)
            .where(Message.conversation_id == conversation_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(self.model.created_at.asc())
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()
