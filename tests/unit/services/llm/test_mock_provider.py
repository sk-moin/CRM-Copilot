from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services.llm.providers.mock_provider import MockProvider
from app.services.llm.models import StreamChunk


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider(get_settings())


@pytest.fixture
def sample_messages():
    return [
        {
            "role": "system",
            "content": "You are CRM Copilot.",
        },
        {
            "role": "user",
            "content": "Hello",
        },
    ]


# ---------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_returns_default_response(
    provider: MockProvider,
    sample_messages,
):
    response = await provider.complete(sample_messages)

    assert isinstance(response, str)
    assert response == provider.DEFAULT_RESPONSE


@pytest.mark.asyncio
async def test_complete_with_model_override(
    provider: MockProvider,
    sample_messages,
):
    response = await provider.complete(
        sample_messages,
        model="mock-model",
    )

    assert response == provider.DEFAULT_RESPONSE


# ---------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_returns_tokens(
    provider: MockProvider,
    sample_messages,
):
    chunks = []

    async for chunk in provider.stream(sample_messages):
        chunks.append(chunk)

    assert len(chunks) > 1

    token_chunks = [
        chunk
        for chunk in chunks
        if chunk.token is not None
    ]

    assert len(token_chunks) > 0

    assert all(
        isinstance(chunk, StreamChunk)
        for chunk in token_chunks
    )


@pytest.mark.asyncio
async def test_stream_final_chunk_contains_usage(
    provider: MockProvider,
    sample_messages,
):
    final = None

    async for chunk in provider.stream(sample_messages):
        final = chunk

    assert final is not None
    assert final.token is None
    assert final.finish_reason == "stop"
    assert final.usage is not None


@pytest.mark.asyncio
async def test_stream_usage_statistics(
    provider: MockProvider,
    sample_messages,
):
    final = None

    async for chunk in provider.stream(sample_messages):
        final = chunk

    usage = final.usage

    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0
    assert usage.total_tokens == (
        usage.prompt_tokens + usage.completion_tokens
    )


@pytest.mark.asyncio
async def test_stream_model_name(
    provider: MockProvider,
    sample_messages,
):
    final = None

    async for chunk in provider.stream(sample_messages):
        final = chunk

    assert final.usage.model == "mock-model"


@pytest.mark.asyncio
async def test_stream_custom_model_name(
    provider: MockProvider,
    sample_messages,
):
    final = None

    async for chunk in provider.stream(
        sample_messages,
        model="gpt-test",
    ):
        final = chunk

    assert final.usage.model == "gpt-test"


@pytest.mark.asyncio
async def test_stream_reconstructs_response(
    provider: MockProvider,
    sample_messages,
):
    response = ""

    async for chunk in provider.stream(sample_messages):
        if chunk.token:
            response += chunk.token

    assert response == provider.DEFAULT_RESPONSE


@pytest.mark.asyncio
async def test_stream_finish_reason(
    provider: MockProvider,
    sample_messages,
):
    final = None

    async for chunk in provider.stream(sample_messages):
        final = chunk

    assert final.finish_reason == "stop"


@pytest.mark.asyncio
async def test_stream_chunk_types(
    provider: MockProvider,
    sample_messages,
):
    async for chunk in provider.stream(sample_messages):
        assert isinstance(chunk, StreamChunk)


@pytest.mark.asyncio
async def test_stream_contains_only_one_final_chunk(
    provider: MockProvider,
    sample_messages,
):
    final_chunks = 0

    async for chunk in provider.stream(sample_messages):
        if chunk.finish_reason is not None:
            final_chunks += 1

    assert final_chunks == 1