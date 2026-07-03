from __future__ import annotations
from uuid import uuid4
import pytest

from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)

from packages.database.models import User
from packages.database.models.conversation import ConversationStatus

@pytest.mark.asyncio
async def test_chat_stream_success(
    authed_client,
    _async_session,
    seeded_tenant,
    seeded_user,
    seeded_organization,
):
    repo = ConversationRepository(
        session=_async_session,
        tenant_id=seeded_tenant.id,
    )

    conversation = await repo.create(
        user_id=seeded_user.id,
        org_id=seeded_organization.id,
        title="Test Chat",
        status=ConversationStatus.ACTIVE,
    )

    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": str(conversation.id),
            "message": "Hello",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/event-stream"
    )

    body = response.text

    assert '"token"' in body
    assert '"finish_reason"' in body
    assert '"conversation_id"' in body



@pytest.mark.asyncio
async def test_chat_stream_invalid_conversation(
    authed_client,
):
    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": str(uuid4()),
            "message": "Hello",
        },
    )

    assert response.status_code == 200
    assert "Conversation" in response.text

    body = response.text

    assert "ValueError" in body
    assert "not found" in body





@pytest.mark.asyncio
async def test_chat_stream_permission_denied(
    authed_client,
    _async_session,
    seeded_tenant,
    seeded_user,
    seeded_organization,
):
    other = User(
        tenant_id=seeded_tenant.id,
        org_id=seeded_organization.id,
        email="other@example.com",
        password_hash="password",
        role="ADMIN",
    )

    _async_session.add(other)
    await _async_session.flush()

    repo = ConversationRepository(
        session=_async_session,
        tenant_id=seeded_tenant.id,
    )

    conversation = await repo.create(
        user_id=other.id,
        org_id=seeded_organization.id,
        title="Private",
        status=ConversationStatus.ACTIVE,
    )

    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": str(conversation.id),
            "message": "Hello",
        },
    )

    assert response.status_code == 200

    body = response.text

    assert "PermissionError" in body



@pytest.mark.asyncio
async def test_chat_stream_empty_message(
    authed_client,
):
    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": None,
            "message": "",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_returns_usage(
    authed_client,
    _async_session,
    seeded_tenant,
    seeded_user,
    seeded_organization,
):
    repo = ConversationRepository(
        session=_async_session,
        tenant_id=seeded_tenant.id,
    )

    conversation = await repo.create(
        user_id=seeded_user.id,
        org_id=seeded_organization.id,
        title="Usage Test",
        status=ConversationStatus.ACTIVE,
    )

    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": str(conversation.id),
            "message": "Hello",
        },
    )

    body = response.text

    assert '"prompt_tokens"' in body
    assert '"completion_tokens"' in body
    assert '"total_tokens"' in body
    assert '"model"' in body