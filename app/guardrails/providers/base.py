"""
Base guardrail provider.

Every guardrail provider must implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.guardrails.models import (
    OutputGuardrailResult,
)
from typing import Any


class GuardrailProvider(ABC):
    """
    Abstract interface for all guardrail providers.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider.

        This method should perform any startup work such as
        loading configuration, initializing SDKs, or validating
        resources.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """
        Execute a guarded LLM request.

        Args:
            messages:
                Chat messages following the application's
                internal message format.

            kwargs:
                Provider-specific arguments.

        Returns:
            Provider-specific response.
        """
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Clean up provider resources.
        """
        raise NotImplementedError

    async def health_check(self) -> dict[str, Any]:
        """
        Return provider health information.

        Providers may override this with more detailed status.
        """
        return {
            "initialized": False,
        }


    @abstractmethod
    async def check_output(
        self,
        text: str,
        user_input: str | None = None,
    ) -> OutputGuardrailResult:
        """Evaluate generated LLM output against configured guardrails."""
        raise NotImplementedError