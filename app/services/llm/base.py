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
from app.services.llm.models import StreamChunk


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

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
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
    ) -> str:
        """Generate a non-streaming completion.

        Args:
            messages:
                Chat messages formatted for the provider.

            model:
                Optional model override.

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