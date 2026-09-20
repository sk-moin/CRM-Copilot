"""
OpenRouter LLM provider.

Uses the OpenAI SDK against the OpenRouter API.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
import json
from app.core.config import Settings
from app.observability.tracing import traced
from app.services.llm.base import LLMProvider
from app.services.llm.models import (
    StreamChunk,
    TokenUsage,
    CompletionResult
)


def _sampling(
    temperature: float | None,
    max_tokens: int | None,
    stop: list[str] | None,
) -> dict[str, Any]:
    """Build sampling kwargs, omitting anything the caller left unset.

    Passing an explicit None to the OpenAI SDK is not the same as omitting
    the key, so unset values must not be forwarded at all.
    """

    options: dict[str, Any] = {}

    if temperature is not None:
        options["temperature"] = temperature

    if max_tokens is not None:
        options["max_tokens"] = max_tokens

    if stop:
        options["stop"] = stop

    return options


class OpenRouterProvider(LLMProvider):
    """OpenRouter implementation of LLMProvider."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": settings.APP_URL,
                "X-OpenRouter-Title": "CRM Copilot",
            },
        )

    @traced(
        name="openrouter-complete",
        run_type="llm",
        tags=["openrouter"],
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

        response = await self._client.chat.completions.create(
            model=model or self.settings.OPENROUTER_MODEL,
            messages=messages,
            **_sampling(temperature, max_tokens, stop),
        )


        if getattr(response, "error", None):
            raise RuntimeError(
                response.error.get(
                    "message",
                    "OpenRouter request failed.",
                )
            )

        if response.choices is None or len(response.choices) == 0:
            raise RuntimeError(
                "OpenRouter returned no completion choices."
            )

        message = response.choices[0].message.content

        if message is None:
            raise RuntimeError(
                "OpenRouter returned an empty completion."
            )

        usage = TokenUsage.empty()

        if response.usage is not None:
            usage = TokenUsage.from_openai(
                response.usage,
                model=model or self.settings.OPENROUTER_MODEL,
            )

        finish_reason = (
            response.choices[0].finish_reason
            if response.choices[0].finish_reason is not None
            else "stop"
        )

        return CompletionResult(
            content=message,
            usage=usage,
            finish_reason=finish_reason,
        )

    @traced(
        name="openrouter-stream",
        run_type="llm",
        tags=["openrouter"],
    )
    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming completion.
        """

        stream = await self._client.chat.completions.create(
            model=model or self.settings.OPENROUTER_MODEL,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **_sampling(temperature, max_tokens, stop),
        )

        finish_reason = "stop"
        usage = TokenUsage.empty()
        model_name = model or self.settings.OPENROUTER_MODEL

        async for chunk in stream:

            # OpenRouter can return an error chunk
            if getattr(chunk, "error", None):
                raise RuntimeError(
                    chunk.error.get(
                        "message",
                        "OpenRouter streaming request failed.",
                    )
                )

            if chunk.choices:
                choice = chunk.choices[0]

                if choice.delta.content:
                    yield StreamChunk.token_chunk(
                        choice.delta.content
                    )

                if choice.finish_reason is not None:
                    finish_reason = choice.finish_reason

            if getattr(chunk, "usage", None) is not None:
                usage = TokenUsage.from_openai(
                    chunk.usage,
                    model=model_name,
                )


        yield StreamChunk.final_chunk(
            finish_reason=finish_reason,
            usage=usage,
        )