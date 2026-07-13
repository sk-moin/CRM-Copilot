"""
ChatService – orchestrates chat workflow with Retrieval-Augmented Generation.

Responsibilities
----------------
* Validate conversation access
* Persist user message
* Load conversation history
* Execute RAG pipeline
* Stream assistant response
* Persist assistant message
* Emit audit events
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.rag_service import RAGService
from app.services.audit_service import AuditService
from app.services.llm.models import (
    StreamChunk,
    TokenUsage,
)
from app.services.llm.prompt_builder import PromptBuilder

from packages.database.models.message import MessageRole
from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)
from packages.database.repositories.message_repository import (
    MessageRepository,
)


class ChatService:
    """
    Service responsible for conversation orchestration.

    ChatService owns:

    - conversation validation
    - message persistence
    - audit logging
    - conversation history

    It delegates Retrieval-Augmented Generation to RAGService.
    """

    def __init__(
        self,
        session: AsyncSession,
        current_user: Any,
        rag_service: RAGService,
    ) -> None:
        self._session = session
        self._user = current_user
        self._tenant_id = current_user.tenant_id

        self._rag_service = rag_service

        self._conversation_repo = ConversationRepository(
            session=session,
            tenant_id=self._tenant_id,
        )

        self._message_repo = MessageRepository(
            session=session,
            tenant_id=self._tenant_id,
        )

        self._audit = AuditService(
            session=session,
            tenant_id=self._tenant_id,
            current_user=current_user,
        )

    
    async def stream_response(
        self,
        conversation_id: UUID,
        user_message: str,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a Retrieval-Augmented response for a conversation.
        """

        # ------------------------------------------------------------------ #
        # Validate conversation ownership
        # ------------------------------------------------------------------ #

        conversation = await self._conversation_repo.get_by_id(
            conversation_id,
        )

        if conversation is None:
            raise ValueError(
                f"Conversation {conversation_id} not found."
            )

        if conversation.user_id != self._user.id:
            raise PermissionError(
                f"Access denied to conversation {conversation_id}."
            )

        # ------------------------------------------------------------------ #
        # Persist user message
        # ------------------------------------------------------------------ #

        user_msg = await self._message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_message,
            tenant_id=self._tenant_id,
        )

        await self._session.flush()

        await self._audit.log_create(
            entity_type="message",
            entity_id=user_msg.id,
            after_values={
                "conversation_id": str(conversation_id),
                "role": "user",
            },
        )

        # ------------------------------------------------------------------ #
        # Load conversation history
        # ------------------------------------------------------------------ #

        history = await self._message_repo.list_for_conversation(
            conversation_id=conversation_id,
            limit=100,
        )

        prompt_messages = PromptBuilder.build(
            system_prompt=PromptBuilder.build_system_prompt(),
            history=history,
            user_message=user_message,
        )

        # Currently PromptBuilder is kept for conversation history.
        # RAGService receives only the latest user query.
        # Future versions can pass prompt_messages into RAGChain if desired.

        start_time = time.time()

        full_response = ""
        usage = TokenUsage.empty()
        finish_reason = "stop"


        # ------------------------------------------------------------------ #
        # Stream RAG response
        # ------------------------------------------------------------------ #

        async for chunk in self._rag_service.stream(
            conversation_id=conversation_id,
            query=user_message,
        ):
        # Final chunk contains metadata only.
            if chunk.is_final:
                finish_reason = chunk.finish_reason or "stop"

                if chunk.usage is not None:
                    usage = chunk.usage

                continue

            if chunk.token:
                full_response += chunk.token

            yield chunk

        # ------------------------------------------------------------------ #
        # Persist assistant message
        # ------------------------------------------------------------------ #

        latency_ms = int(
            (time.time() - start_time) * 1000,
        )

        assistant_msg = await self._message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=full_response,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )

        await self._session.flush()

        # ------------------------------------------------------------------ #
        # Update conversation timestamp
        # ------------------------------------------------------------------ #

        await self._conversation_repo.update(
            conversation_id,
            updated_at=datetime.now(UTC),
        )

        # ------------------------------------------------------------------ #
        # Audit assistant message
        # ------------------------------------------------------------------ #

        await self._audit.log_create(
            entity_type="message",
            entity_id=assistant_msg.id,
            after_values={
                "conversation_id": str(conversation_id),
                "role": "assistant",
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "model": usage.model,
                },
            },
        )

        # ------------------------------------------------------------------ #
        # Commit transaction
        # ------------------------------------------------------------------ #

        await self._session.commit()

        # ------------------------------------------------------------------ #
        # Emit final metadata chunk
        # ------------------------------------------------------------------ #

        yield StreamChunk(
            finish_reason=finish_reason,
            usage=usage,
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
        )