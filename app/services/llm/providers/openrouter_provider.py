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
    ) -> CompletionResult:

        print("=" * 80)
        print("MESSAGES SENT TO OPENROUTER")
        print(json.dumps(messages, indent=2))
        print("=" * 80)

        response = await self._client.chat.completions.create(
            model=model or self.settings.OPENROUTER_MODEL,
            messages=messages,
        )

        print("=" * 80)
        print("OPENROUTER RAW RESPONSE")
        print("=" * 80)
        print(response)
        print("=" * 80)

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

        print(message)

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
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming completion.
        """

        stream = await self._client.chat.completions.create(
            model=model or self.settings.OPENROUTER_MODEL,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
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

            print(chunk)

        yield StreamChunk.final_chunk(
            finish_reason=finish_reason,
            usage=usage,
        )