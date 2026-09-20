"""Abstract interface for Large Language Model providers.

The service layer depends only on this abstraction, allowing the application
to support multiple LLM backends (OpenAI, Anthropic, Gemini, local models,
etc.) without changing business logic.

Providers must remain stateless. They should not maintain mutable request
state such as token counters or conversation history. Instead, usage
statistics are returned via the final StreamChunk emitted during streaming.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import Settings
from app.services.llm.models import StreamChunk, CompletionResult


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the provider with application settings.

        Args:
            settings: Application configuration.
        """
        self._settings = settings

    @property
    def settings(self) -> Settings:
        """Return the provider configuration."""
        return self._settings

    @property
    def default_model(self) -> str:
        """The model this provider uses when a caller does not name one.

        Exists so other layers can ask the provider instead of keeping their
        own provider-name-to-model mapping. A duplicated mapping silently
        returns the wrong model for any provider it has not been taught about,
        which is how the guardrail judge came to be called with "mock-model"
        against a live API.
        """

        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response.

        Args:
            messages:
                Chat messages already formatted for the provider.
                Each message should contain at least:

                {
                    "role": "...",
                    "content": "...",
                }

            model:
                Optional model override.
                If None, the provider should use its configured default model.

        Yields:
            StreamChunk instances.

            Normal chunks contain incremental text.

            The final chunk should contain:

            - finish_reason
            - usage (if available)

        Raises:
            Provider-specific exceptions (authentication, connection,
            rate-limit, etc.) should be allowed to propagate. Business
            translation is handled by ChatService.
        """
        raise NotImplementedError

    @abstractmethod
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
                Chat messages formatted for the provider.

            model:
                Optional model override.

            temperature, max_tokens, stop:
                Optional sampling controls. When None the provider's own
                default applies, so existing callers are unaffected. These
                exist because callers that need a constrained, parseable
                answer — the guardrail judge in particular — must be able to
                pin temperature and stop tokens. An unpinned judge that
                answers in prose is read as a policy violation.

        Returns:
            Complete assistant response.

        Raises:
            Provider-specific exceptions.

        Notes:
            This method is intended for future features such as:

            - title generation
            - summarization
            - structured outputs
            - evaluation
        """
        raise NotImplementedError