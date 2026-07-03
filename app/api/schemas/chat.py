"""Pydantic schemas for Chat APIs.

These schemas define the public HTTP contract for the Streaming Chat API
(Spec 004). They intentionally contain only request/response models.

Provider-specific domain models such as StreamChunk and TokenUsage live in
``app.services.llm.models`` and are imported where needed rather than
duplicated here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Request Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """Request payload for the streaming chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        description="User message to send to the assistant.",
    )

    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation ID. If omitted, a new conversation is created.",
    )


# ============================================================================
# Conversation Schemas
# ============================================================================


class ConversationResponse(BaseModel):
    """Conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    org_id: UUID | None = None
    user_id: UUID

    title: str | None = None
    status: str

    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, conversation: Any) -> "ConversationResponse":
        """Create a response model from a Conversation ORM instance."""

        return cls(
            id=conversation.id,
            tenant_id=conversation.tenant_id,
            org_id=conversation.org_id,
            user_id=conversation.user_id,
            title=conversation.title,
            status=(
                conversation.status.value
                if hasattr(conversation.status, "value")
                else str(conversation.status)
            ),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationListResponse(BaseModel):
    """Paginated conversation list."""

    items: list[ConversationResponse]
    total: int


# ============================================================================
# Message Schemas
# ============================================================================


class MessageResponse(BaseModel):
    """Message response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID

    role: str
    content: str

    model: str | None = None

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    latency_ms: int | None = None

    finish_reason: str | None = None

    message_metadata: dict[str, Any] | None = None

    created_at: datetime

    @classmethod
    def from_model(cls, message: Any) -> "MessageResponse":
        """Create a response model from a Message ORM instance."""

        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            role=(
                message.role.value
                if hasattr(message.role, "value")
                else str(message.role)
            ),
            content=message.content,
            model=message.model,
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            total_tokens=message.total_tokens,
            latency_ms=message.latency_ms,
            finish_reason=message.finish_reason,
            message_metadata=message.message_metadata,
            created_at=message.created_at,
        )


# ============================================================================
# SSE Event Schemas
# ============================================================================


class ChatStreamStart(BaseModel):
    """First SSE event."""

    conversation_id: UUID


class ChatStreamToken(BaseModel):
    """Streaming token event."""

    token: str


class ChatStreamUsage(BaseModel):
    """Final usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    model: str | None = None

    latency_ms: int | None = None


class ChatStreamDone(BaseModel):
    """Final stream completion event."""

    conversation_id: UUID
    message_id: UUID

    finish_reason: str = "stop"


class ChatStreamError(BaseModel):
    """Streaming error event."""

    type: str
    message: str


# ============================================================================
# Conversation Update
# ============================================================================


class ConversationUpdate(BaseModel):
    """Conversation update request."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )


# ============================================================================
# Generic Usage Response
# ============================================================================


class UsageResponse(BaseModel):
    """Token usage response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    model: str | None = None

    latency_ms: int | None = None