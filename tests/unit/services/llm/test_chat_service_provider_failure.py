from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from app.core.config import get_settings
from app.services.chat_service import ChatService
from app.services.llm.base import LLMProvider
from app.services.llm.models import StreamChunk
from packages.database.models.message import MessageRole
from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)
from packages.database.repositories.message_repository import (
    MessageRepository,
)
from packages.database.models.conversation import ConversationStatus


# ---------------------------------------------------------------------
# Provider that always fails
# ---------------------------------------------------------------------


class FailingProvider(LLMProvider):
    """Mock provider that raises an exception during streaming."""

    def __init__(self):
        super().__init__(get_settings())

    async def stream(
        self,
        messages,
        model=None,
    ) -> AsyncIterator[StreamChunk]:
        raise RuntimeError("LLM provider unavailable")
        yield  # pragma: no cover

    async def complete(
        self,
        messages,
        model=None,
    ) -> str:
        raise RuntimeError("LLM provider unavailable")


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def conversation(
    async_session,
    tenant,
    organization,
    user,
):
    repo = ConversationRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    return await repo.create(
        user_id=user.id,
        org_id=organization.id,
        title="Failure Test",
        status=ConversationStatus.ACTIVE,
    )


@pytest_asyncio.fixture
async def service(
    async_session,
    user,
):
    return ChatService(
        session=async_session,
        current_user=user,
        provider=FailingProvider(),
    )


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_exception_is_propagated(
    service,
    conversation,
):
    with pytest.raises(RuntimeError, match="LLM provider unavailable"):
        async for _ in service.stream_response(
            conversation.id,
            "Hello",
        ):
            pass


@pytest.mark.asyncio
async def test_user_message_is_saved_before_provider_failure(
    async_session,
    tenant,
    service,
    conversation,
):
    with pytest.raises(RuntimeError):
        async for _ in service.stream_response(
            conversation.id,
            "Hello",
        ):
            pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assert len(history) == 1
    assert history[0].role == MessageRole.USER
    assert history[0].content == "Hello"


@pytest.mark.asyncio
async def test_assistant_message_not_saved_after_failure(
    async_session,
    tenant,
    service,
    conversation,
):
    with pytest.raises(RuntimeError):
        async for _ in service.stream_response(
            conversation.id,
            "Hello",
        ):
            pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assistant_messages = [
        msg
        for msg in history
        if msg.role == MessageRole.ASSISTANT
    ]

    assert assistant_messages == []


@pytest.mark.asyncio
async def test_only_user_message_exists(
    async_session,
    tenant,
    service,
    conversation,
):
    with pytest.raises(RuntimeError):
        async for _ in service.stream_response(
            conversation.id,
            "Testing failure",
        ):
            pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assert len(history) == 1
    assert history[0].role == MessageRole.USER


@pytest.mark.asyncio
async def test_no_usage_metadata_saved_when_provider_fails(
    async_session,
    tenant,
    service,
    conversation,
):
    with pytest.raises(RuntimeError):
        async for _ in service.stream_response(
            conversation.id,
            "Hello",
        ):
            pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    user_message = history[0]

    assert user_message.role == MessageRole.USER

    # Assistant message should not exist, therefore no usage metadata
    assert len(history) == 1