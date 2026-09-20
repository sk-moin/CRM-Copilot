"""OpenAI provider implementation.

Uses the modern OpenAI Python SDK (openai>=1.x) with AsyncOpenAI.

This provider is intentionally stateless. It is responsible only for
communicating with the OpenAI API and converting provider responses into
provider-agnostic StreamChunk objects.

Business concerns such as:

- retry policy
- audit logging
- latency measurement
- usage persistence
- SSE formatting
- database writes

are handled by ChatService.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.models import (
    CompletionResult,
    StreamChunk,
    TokenUsage,
)


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of the LLMProvider interface."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )

        self._default_model = settings.OPENAI_DEFAULT_MODEL

    @property
    def default_model(self) -> str:
        return self.settings.OPENAI_MODEL

    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion from OpenAI.

        Args:
            messages:
                Provider-ready chat messages.

            model:
                Optional model override.

        Yields:
            StreamChunk objects.

        Raises:
            OpenAI SDK exceptions directly. ChatService is responsible for
            translating them into application-level events.
        """

        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        usage: TokenUsage | None = None
        finish_reason: str | None = None

        async for chunk in response:
            if chunk.usage is not None:
                usage = TokenUsage.from_openai(
                    chunk.usage,
                    model=model or self._default_model,
                )

            if not chunk.choices:
                continue

            choice = chunk.choices[0]

            if choice.delta.content:
                yield StreamChunk.token_chunk(choice.delta.content)

            if choice.finish_reason is not None:
                finish_reason = choice.finish_reason

        yield StreamChunk.final_chunk(
            finish_reason=finish_reason or "stop",
            usage=usage,
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> CompletionResult:
        """Generate a non-streaming completion.

        Args:
            messages:
                Provider-ready chat messages.

            model:
                Optional model override.

        Returns:
            Complete assistant response.

        Raises:
            OpenAI SDK exceptions directly.
        """

        response = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            stream=False,
        )

        if not response.choices:
            return CompletionResult(
                content="",
                usage=TokenUsage.empty(),
                finish_reason="stop",
            )

        message = response.choices[0].message

        return CompletionResult(
            content=message.content or "",
            usage=TokenUsage.empty(),
            finish_reason="stop",
        )