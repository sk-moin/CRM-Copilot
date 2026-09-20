"""
Adapter between CRM Copilot's LLMProvider and NVIDIA NeMo Guardrails.

NeMo Guardrails 0.23 exposes the LLMModel protocol. This adapter allows
NeMo to use the application's existing LLMProvider abstraction instead
of creating a separate LLM client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from nemoguardrails.types import (
    ChatMessage,
    LLMResponse,
    LLMResponseChunk,
)

from app.services.llm.base import LLMProvider
from app.services.llm.models import CompletionResult


def _sampling_from(
    stop: list[str] | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Translate NeMo's call options into LLMProvider sampling arguments.

    NeMo invokes the judge as `generate_async(prompt, stop=stop, **llm_params)`,
    where llm_params carries the task's temperature and token cap. Dropping
    them lets the judge answer at the provider's default temperature and run
    past the expected one-word reply. That matters because NeMo's
    `is_content_safe` reads only the first two words and treats anything it
    does not recognize as a policy violation, so a chatty judge silently
    blocks a perfectly good answer.

    Unknown kwargs are ignored rather than forwarded: the provider interface
    accepts a fixed set, and passing arbitrary keys through would fail loudly
    on a NeMo upgrade that adds one.
    """

    options: dict[str, Any] = {}

    if stop:
        options["stop"] = stop

    temperature = kwargs.get("temperature")
    if temperature is not None:
        options["temperature"] = temperature

    max_tokens = kwargs.get("max_tokens")
    if max_tokens is not None:
        options["max_tokens"] = max_tokens

    return options


class GuardrailLLMAdapter:
    """
    NeMo-compatible LLM adapter.

    The adapter delegates all actual model calls to the existing
    application LLMProvider.
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str,
    ) -> None:
        self._provider = provider
        self._model = model

    @property
    def model_name(self) -> str:
        """Return the configured model name."""
        return self._model

    @property
    def provider_name(self) -> str | None:
        """Return the application LLM provider name."""
        return getattr(
            self._provider.settings,
            "LLM_PROVIDER",
            None,
        )

    @property
    def provider_url(self) -> str | None:
        """Return the provider endpoint when available."""

        provider_name = self.provider_name

        if provider_name == "openrouter":
            return "https://openrouter.ai/api/v1"

        if provider_name == "openai":
            return getattr(
                self._provider.settings,
                "OPENAI_BASE_URL",
                None,
            )

        return None

    async def generate_async(
        self,
        prompt: str | list[ChatMessage],
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response using the existing LLMProvider.
        """

        messages = self._convert_messages(prompt)

        result = await self._provider.complete(
            messages=messages,
            model=self._model,
            **_sampling_from(stop, kwargs),
        )

        content: str
        finish_reason = "stop"

        if isinstance(result, CompletionResult):
            content = result.content
            finish_reason = result.finish_reason or "stop"

        elif isinstance(result, str):
            # Defensive only. Every in-tree provider returns a CompletionResult
            # now; this tolerates a third-party implementation that does not.
            content = result

        else:
            # Defensive compatibility for provider implementations
            # returning a CompletionResult-like object.
            content = getattr(result, "content", None)

            if not isinstance(content, str):
                raise TypeError(
                    "LLM provider returned an unsupported completion result."
                )

            finish_reason = (
                getattr(result, "finish_reason", None)
                or "stop"
            )

        return LLMResponse(
            content=content,
            model=self._model,
            finish_reason=finish_reason,
        )

    async def stream_async(
        self,
        prompt: str | list[ChatMessage],
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponseChunk]:
        """
        Stream a response through the existing LLMProvider.
        """

        messages = self._convert_messages(prompt)

        async for chunk in self._provider.stream(
            messages=messages,
            model=self._model,
            **_sampling_from(stop, kwargs),
        ):
            if chunk.token:
                yield LLMResponseChunk(
                    delta_content=chunk.token,
                    model=self._model,
                )

            if chunk.finish_reason:
                yield LLMResponseChunk(
                    model=self._model,
                    finish_reason=chunk.finish_reason,
                )

    @staticmethod
    def _convert_messages(
        prompt: str | list[ChatMessage],
    ) -> list[dict[str, Any]]:
        """
        Convert NeMo ChatMessage objects into the application's
        provider-neutral message format.
        """

        if isinstance(prompt, str):
            return [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]

        messages: list[dict[str, Any]] = []

        for message in prompt:
            item: dict[str, Any] = {
                "role": message.role,
                "content": message.content,
            }

            if getattr(message, "name", None):
                item["name"] = message.name

            if getattr(message, "tool_call_id", None):
                item["tool_call_id"] = message.tool_call_id

            if getattr(message, "tool_calls", None):
                item["tool_calls"] = message.tool_calls

            messages.append(item)

        return messages