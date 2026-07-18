from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from app.services.chat_service import ChatService
from app.services.llm.providers.mock_provider import MockProvider
from app.core.config import get_settings
from app.services.llm.models import StreamChunk, TokenUsage

from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)
from packages.database.repositories.message_repository import (
    MessageRepository,
)
from packages.database.models.conversation import ConversationStatus


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest_asyncio.fixture
async def conversation(async_session, tenant, organization, user):
    repo = ConversationRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    conversation = await repo.create(
        user_id=user.id,
        org_id=organization.id,
        title="Test Conversation",
        status=ConversationStatus.ACTIVE,
    )

    return conversation


@pytest.fixture
def mock_provider():
    return MockProvider(get_settings())




@pytest_asyncio.fixture
async def chat_service(async_session, user):

    class FakeAgentService:
        async def run(
            self,
            *,
            conversation_id,
            tenant_id,
            user_id,
            query,
        ):
            return {
                "conversation_id": conversation_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "query": query,
                "messages": [],
                "retrieved_documents": [],
                "retrieval_metadata": {},
                "prompt": "",
                "response": "Mock response",
                "citations": [],
                "usage": TokenUsage(
                    prompt_tokens=8,
                    completion_tokens=4,
                    total_tokens=12,
                    model="mock-model",
                ),
                "finish_reason": "stop",
                "errors": [],
            }

    return ChatService(
        session=async_session,
        current_user=user,
        agent_service=FakeAgentService(),
    )


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_response_success(
    chat_service,
    conversation,
):
    chunks = []

    async for chunk in chat_service.stream_response(
        conversation.id,
        "Hello",
    ):
        chunks.append(chunk)

    assert len(chunks) > 0

    final = chunks[-1]

    assert final.finish_reason == "stop"
    assert final.usage is not None
    assert final.message_id is not None
    assert final.conversation_id == conversation.id


@pytest.mark.asyncio
async def test_user_message_persisted(
    async_session,
    tenant,
    chat_service,
    conversation,
):
    async for _ in chat_service.stream_response(
        conversation.id,
        "Persist me",
    ):
        pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assert len(history) == 2

    assert history[0].role.value == "user"
    assert history[0].content == "Persist me"


@pytest.mark.asyncio
async def test_assistant_message_persisted(
    async_session,
    tenant,
    chat_service,
    conversation,
):
    async for _ in chat_service.stream_response(
        conversation.id,
        "Hi",
    ):
        pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assistant = history[-1]

    assert assistant.role.value == "assistant"
    assert assistant.content != ""
    assert assistant.model == "mock-model"


@pytest.mark.asyncio
async def test_invalid_conversation(chat_service):
    with pytest.raises(ValueError):
        async for _ in chat_service.stream_response(
            uuid4(),
            "Hello",
        ):
            pass


@pytest.mark.asyncio
async def test_permission_denied(
    async_session,
    tenant,
    organization,
    user,
    mock_provider,
):
    from packages.database.models import User

    other_user = User(
        tenant_id=tenant.id,
        org_id=organization.id,
        email="other@example.com",
        password_hash="password",
        role="ADMIN",
    )

    async_session.add(other_user)
    await async_session.flush()

    repo = ConversationRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    conversation = await repo.create(
        user_id=other_user.id,
        org_id=organization.id,
        title="Private",
        status=ConversationStatus.ACTIVE,
    )

    agent_service = AsyncMock()

    service = ChatService(
        session=async_session,
        current_user=user,
        agent_service=agent_service,
    )

    with pytest.raises(PermissionError):
        async for _ in service.stream_response(
            conversation.id,
            "Hello",
        ):
            pass


@pytest.mark.asyncio
async def test_usage_metadata_saved(
    async_session,
    tenant,
    chat_service,
    conversation,
):
    async for _ in chat_service.stream_response(
        conversation.id,
        "Token test",
    ):
        pass

    repo = MessageRepository(
        session=async_session,
        tenant_id=tenant.id,
    )

    history = await repo.list_for_conversation(conversation.id)

    assistant = history[-1]

    assert assistant.prompt_tokens > 0
    assert assistant.completion_tokens > 0
    assert assistant.total_tokens > 0
    assert assistant.latency_ms >= 0