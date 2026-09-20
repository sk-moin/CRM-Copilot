"""
Groq LLM provider.

Groq serves an OpenAI-compatible API, so this uses the OpenAI SDK pointed at
Groq's base URL rather than adding another client library. The shape mirrors
`OpenRouterProvider` deliberately: two providers that behave differently under
the same interface are a source of bugs that only show up after a switch.

Groq-specific notes:

- `stop` accepts at most 4 sequences. More than that is a 400 from the API, so
  the list is truncated here rather than failing the request.
- Usage is reported in the final streaming chunk, as with OpenAI, but Groq also
  attaches an `x_groq` object; nothing here depends on it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.observability.tracing import traced
from app.services.llm.base import LLMProvider
from app.services.llm.models import (
    CompletionResult,
    StreamChunk,
    TokenUsage,
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq rejects a request carrying more than four stop sequences.
MAX_STOP_SEQUENCES = 4


def _sampling(
    temperature: float | None,
    max_tokens: int | None,
    stop: list[str] | None,
) -> dict[str, Any]:
    """Build sampling kwargs, omitting anything the caller left unset.

    Passing an explicit None to the OpenAI SDK is not the same as omitting the
    key, so unset values must not be forwarded at all.
    """

    options: dict[str, Any] = {}

    if temperature is not None:
        options["temperature"] = temperature

    if max_tokens is not None:
        options["max_tokens"] = max_tokens

    if stop:
        # Truncate rather than let the API reject the whole request. The
        # guardrail judge passes task stop tokens and does not know the limit.
        options["stop"] = list(stop)[:MAX_STOP_SEQUENCES]

    return options


class GroqProvider(LLMProvider):
    """Groq implementation of LLMProvider."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self._client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
        )

    @property
    def default_model(self) -> str:
        return self.settings.GROQ_MODEL

    @traced(
        name="groq-complete",
        run_type="llm",
        tags=["groq"],
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
        model_name = model or self.settings.GROQ_MODEL

        response = await self._client.chat.completions.create(
            model=model_name,
            messages=messages,
            **_sampling(temperature, max_tokens, stop),
        )

        if not response.choices:
            raise RuntimeError("Groq returned no completion choices.")

        message = response.choices[0].message.content

        if message is None:
            raise RuntimeError("Groq returned an empty completion.")

        usage = TokenUsage.empty()

        if response.usage is not None:
            usage = TokenUsage.from_openai(response.usage, model=model_name)

        finish_reason = response.choices[0].finish_reason or "stop"

        return CompletionResult(
            content=message,
            usage=usage,
            finish_reason=finish_reason,
        )

    @traced(
        name="groq-stream",
        run_type="llm",
        tags=["groq"],
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
        """Generate a streaming completion."""

        model_name = model or self.settings.GROQ_MODEL

        stream = await self._client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **_sampling(temperature, max_tokens, stop),
        )

        finish_reason = "stop"
        usage = TokenUsage.empty()

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]

                if choice.delta.content:
                    yield StreamChunk.token_chunk(choice.delta.content)

                if choice.finish_reason is not None:
                    finish_reason = choice.finish_reason

            # The usage-bearing chunk carries no choices, so this is checked
            # independently of the branch above.
            if getattr(chunk, "usage", None) is not None:
                usage = TokenUsage.from_openai(chunk.usage, model=model_name)

        yield StreamChunk.final_chunk(
            finish_reason=finish_reason,
            usage=usage,
        )
