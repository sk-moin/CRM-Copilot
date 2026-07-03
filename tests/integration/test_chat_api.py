from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from packages.database.repositories.conversation_repository import (
    ConversationRepository,
)
from packages.database.models.conversation import ConversationStatus

@pytest.mark.asyncio
async def test_chat_stream_endpoint(
    authed_client: AsyncClient,
    _async_session,
    seeded_user,
):
    """
    Verify the streaming endpoint returns SSE events.
    """

    conversation_repo = ConversationRepository(
        session=_async_session,
        tenant_id=seeded_user.tenant_id,
    )

    conversation = await conversation_repo.create(
        user_id=seeded_user.id,
        title="Streaming Test",
        status=ConversationStatus.ACTIVE,
    )

    response = await authed_client.post(
        "/chat/stream",
        json={
            "conversation_id": str(conversation.id),
            "message": "Hello!",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/event-stream"
    )

    body = response.text

    assert "token" in body
    assert "prompt_tokens" in body
    assert "completion_tokens" in body
    assert "message_id" in body