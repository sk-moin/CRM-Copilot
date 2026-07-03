# app/services/conversation_service.py

from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.conversation import Conversation
from packages.database.repositories.conversation_repository import ConversationRepository
from app.services.audit_service import AuditService


class ConversationService:
    def __init__(self, *, session: AsyncSession, tenant_id: UUID, current_user: Optional[Any] = None):
        """
        Initialize conversation service with tenant isolation and audit tracking.

        Args:
            session: Async database session
            tenant_id: Tenant identifier
            current_user: Authenticated user (may be None)
        """
        self._session = session
        self._tenant_id = tenant_id
        self._current_user = current_user
        self._repo = ConversationRepository(
            session=session,
            tenant_id=tenant_id,
        )
        self._audit = AuditService(
            session=session,
            tenant_id=tenant_id,
            current_user=current_user,
        )

    async def create(self, title: str, user_id: UUID) -> Optional[Conversation]:
        """
        Create a new conversation for a user.

        Args:
            title: Conversation title
            user_id: User who owns the conversation

        Returns:
            Created conversation object or None if fails
        """
        conversation = await self._repo.create(
            title=title,
            user_id=user_id,
        )

        # Audit creation
        await self._audit.log_create(
            entity_type="conversation",
            entity_id=conversation.id,
            after_values={
                "title": conversation.title,
                "status": conversation.status.value,
                "user_id": str(conversation.user_id),
            },
        )

        return conversation

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a conversation by ID.

        Args:
            conversation_id: ID of conversation to retrieve

        Returns:
            Conversation object or None if not found
        """
        return await self._repo.get_by_id(conversation_id)

    async def list_for_user(self, user_id: UUID) -> List[Conversation]:
        """
        List all non-deleted conversations for a user.

        Args:
            user_id: User to list conversations for

        Returns:
            List of conversation objects
        """
        return await self._repo.list_for_user(user_id=user_id)

    async def rename(self, conversation_id: UUID, title: str) -> bool:
        """
        Rename a conversation.

        Args:
            conversation_id: ID of conversation to rename
            title: New title for conversation

        Returns:
            True if successful, False if conversation not found
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False
        
        old_title = conversation.title

        updated = await self._repo.update(
            conversation_id,
            title=title,
        )

        if updated:
            await self._audit.log_update(
                entity_type="conversation",
                entity_id=conversation_id,
                before_values={"title": old_title},
                after_values={"title": updated.title},
            )

        return bool(updated)

    async def archive(self, conversation_id: UUID) -> bool:
        """
        Soft-delete a conversation.

        Args:
            conversation_id: ID of conversation to archive

        Returns:
            True if successful, False if conversation not found
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False

        before_values = {
            "id": str(conversation.id),
            "title": conversation.title,
            "status": conversation.status.value,
        }
        deleted = await self._repo.soft_delete(conversation_id)

        if deleted:
            await self._audit.log_delete(
                entity_type="conversation",
                entity_id=conversation_id,
                before_values=before_values,
            )

        return bool(deleted)