import asyncio
from uuid import uuid4

import pytest

from packages.database.models.conversation import Conversation
from packages.database.models.message import Message, MessageRole
from packages.database.repositories.message_repository import MessageRepository


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

@pytest.fixture
async def message_repository(async_session, tenant):
    """Tenant-scoped repository."""
    return MessageRepository(async_session, tenant.id)


@pytest.fixture
async def test_conversation(
    async_session,
    tenant,
    organization,
    user,
):
    """
    Persist a valid conversation.

    Uses the real user fixture so the FK constraint passes.
    """
    conversation = Conversation(
        tenant_id=tenant.id,
        org_id=organization.id,
        user_id=user.id,
        title="Test Conversation",
        status="active",
    )

    async_session.add(conversation)
    await async_session.flush()
    await async_session.refresh(conversation)

    return conversation


@pytest.fixture
async def test_message(
    async_session,
    tenant,
    test_conversation,
):
    """Persist a message."""
    message = Message(
        tenant_id=tenant.id,
        conversation_id=test_conversation.id,
        role=MessageRole.USER,
        content="Hello CRM Copilot!",
    )

    async_session.add(message)
    await async_session.flush()
    await async_session.refresh(message)

    return message


# ---------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_message(
    message_repository,
    test_conversation,
):
    message = await message_repository.create(
        conversation_id=test_conversation.id,
        role=MessageRole.USER,
        content="Test message",
    )

    assert message.id is not None
    assert message.tenant_id == message_repository.tenant_id
    assert message.content == "Test message"


# ---------------------------------------------------------------------
# get_by_id()
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_by_id_returns_message(
    message_repository,
    test_message,
):
    result = await message_repository.get_by_id(test_message.id)

    assert result is not None
    assert result.id == test_message.id
    assert result.content == test_message.content


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown_message(
    message_repository,
):
    result = await message_repository.get_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_excludes_soft_deleted_conversation(
    message_repository,
    async_session,
    test_conversation,
    test_message,
):
    test_conversation.deleted_at = test_conversation.created_at

    await async_session.flush()

    result = await message_repository.get_by_id(test_message.id)

    assert result is None


# ---------------------------------------------------------------------
# list_for_conversation()
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_for_conversation_returns_history(
    message_repository,
    async_session,
    tenant,
    test_conversation,
):
    async_session.add_all(
        [
            Message(
                tenant_id=tenant.id,
                conversation_id=test_conversation.id,
                role=MessageRole.USER,
                content="First",
            ),
            Message(
                tenant_id=tenant.id,
                conversation_id=test_conversation.id,
                role=MessageRole.ASSISTANT,
                content="Second",
            ),
        ]
    )

    await async_session.flush()

    history = await message_repository.list_for_conversation(
        test_conversation.id
    )

    assert len(history) == 2
    assert history[0].content == "First"
    assert history[1].content == "Second"


@pytest.mark.asyncio
async def test_list_for_conversation_orders_by_created_at(
    message_repository,
    async_session,
    tenant,
    test_conversation,
):
    for i in range(5):
        async_session.add(
            Message(
                tenant_id=tenant.id,
                conversation_id=test_conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}",
            )
        )

        await asyncio.sleep(0.01)

    await async_session.flush()

    history = await message_repository.list_for_conversation(
        test_conversation.id
    )

    timestamps = [m.created_at for m in history]

    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_list_for_conversation_pagination(
    message_repository,
    async_session,
    tenant,
    test_conversation,
):
    for i in range(10):
        async_session.add(
            Message(
                tenant_id=tenant.id,
                conversation_id=test_conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}",
            )
        )

    await async_session.flush()

    page = await message_repository.list_for_conversation(
        test_conversation.id,
        limit=5,
        offset=0,
    )

    assert len(page) == 5


@pytest.mark.asyncio
async def test_list_for_conversation_excludes_soft_deleted_conversation(
    message_repository,
    async_session,
    tenant,
    test_conversation,
):
    async_session.add(
        Message(
            tenant_id=tenant.id,
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Hidden message",
        )
    )

    await async_session.flush()

    test_conversation.deleted_at = test_conversation.created_at

    await async_session.flush()

    history = await message_repository.list_for_conversation(
        test_conversation.id
    )

    assert history == []


# ---------------------------------------------------------------------
# Repository API
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_message_repository_uses_base_repository_crud(
    message_repository,
):
    """
    MessageRepository intentionally inherits CRUD from BaseRepository.
    It does not override update/delete.
    """

    assert callable(message_repository.create)
    assert callable(message_repository.get_by_id)
    assert callable(message_repository.update)
    assert callable(message_repository.delete)