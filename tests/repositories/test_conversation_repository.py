# tests/repositories/test_conversation_repository.py

from __future__ import annotations

import uuid

import pytest

from packages.database.models.conversation import Conversation, ConversationStatus
from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
async def conversation_repository(async_session, tenant):
    return ConversationRepository(
        session=async_session,
        tenant_id=tenant.id,
    )


# --------------------------------------------------------------------------
# CREATE
# --------------------------------------------------------------------------

async def test_create_conversation(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        title="Test Conversation",
    )

    assert conversation.id is not None
    assert conversation.tenant_id == conversation_repository.tenant_id
    assert conversation.org_id == organization.id
    assert conversation.user_id == user.id
    assert conversation.title == "Test Conversation"
    assert conversation.status == ConversationStatus.ACTIVE


# --------------------------------------------------------------------------
# GET BY ID
# --------------------------------------------------------------------------

async def test_get_by_id(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    found = await conversation_repository.get_by_id(conversation.id)

    assert found is not None
    assert found.id == conversation.id


async def test_get_by_id_returns_none_for_unknown(
    conversation_repository,
):
    result = await conversation_repository.get_by_id(uuid.uuid4())

    assert result is None


async def test_get_by_id_excludes_soft_deleted(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    await conversation_repository.soft_delete(conversation.id)

    result = await conversation_repository.get_by_id(conversation.id)

    assert result is None


# --------------------------------------------------------------------------
# UPDATE
# --------------------------------------------------------------------------

async def test_update_title_and_status(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    updated = await conversation_repository.update(
        conversation.id,
        title="Updated Title",
        status=ConversationStatus.ARCHIVED,
    )

    assert updated.title == "Updated Title"
    assert updated.status == ConversationStatus.ARCHIVED


async def test_update_ignores_forbidden_fields(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    updated = await conversation_repository.update(
        conversation.id,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        created_at=None,
    )

    assert updated is not None
    assert updated.tenant_id == conversation.tenant_id
    assert updated.user_id == conversation.user_id


async def test_update_returns_none_for_unknown(
    conversation_repository,
):
    result = await conversation_repository.update(
        uuid.uuid4(),
        title="New Title",
    )

    assert result is None


# --------------------------------------------------------------------------
# SOFT DELETE
# --------------------------------------------------------------------------

async def test_soft_delete(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    deleted = await conversation_repository.soft_delete(
        conversation.id,
    )

    assert deleted is not None
    assert deleted.deleted_at is not None


async def test_soft_delete_unknown_returns_none(
    conversation_repository,
):
    result = await conversation_repository.soft_delete(
        uuid.uuid4(),
    )

    assert result is None


# --------------------------------------------------------------------------
# LIST FOR USER
# --------------------------------------------------------------------------

async def test_list_for_user(
    conversation_repository,
    organization,
    user,
):
    first = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        title="Conversation 1",
    )

    second = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        title="Conversation 2",
    )

    conversations = await conversation_repository.list_for_user(
        user.id,
    )

    ids = {c.id for c in conversations}

    assert first.id in ids
    assert second.id in ids


async def test_list_for_user_status_filter(
    conversation_repository,
    organization,
    user,
):
    await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        status=ConversationStatus.ACTIVE,
    )

    archived = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        status=ConversationStatus.ARCHIVED,
    )

    conversations = await conversation_repository.list_for_user(
        user.id,
        status=ConversationStatus.ARCHIVED,
    )

    assert len(conversations) == 1
    assert conversations[0].id == archived.id


async def test_list_for_user_pagination(
    conversation_repository,
    organization,
    user,
):
    for i in range(5):
        await conversation_repository.create(
            org_id=organization.id,
            user_id=user.id,
            title=f"Conversation {i}",
        )

    first_page = await conversation_repository.list_for_user(
        user.id,
        limit=2,
        offset=0,
    )

    second_page = await conversation_repository.list_for_user(
        user.id,
        limit=2,
        offset=2,
    )

    assert len(first_page) == 2
    assert len(second_page) == 2


async def test_list_for_user_excludes_soft_deleted(
    conversation_repository,
    organization,
    user,
):
    conversation = await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
    )

    await conversation_repository.soft_delete(
        conversation.id,
    )

    conversations = await conversation_repository.list_for_user(
        user.id,
    )

    ids = {c.id for c in conversations}

    assert conversation.id not in ids


async def test_list_for_user_orders_by_created_at_desc(
    conversation_repository,
    organization,
    user,
):
    await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        title="First",
    )

    await conversation_repository.create(
        org_id=organization.id,
        user_id=user.id,
        title="Second",
    )

    conversations = await conversation_repository.list_for_user(
        user.id,
    )

    assert conversations[0].created_at >= conversations[1].created_at