"""
Exceptions used by the guardrails layer.
"""

from __future__ import annotations


class GuardrailError(Exception):
    """
    Base exception for guardrail-related failures.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "GUARDRAIL_ERROR",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class GuardrailInputBlockedError(GuardrailError):
    """
    Raised when an input violates an input guardrail policy.
    """

    def __init__(
        self,
        message: str = (
            "The request was blocked by the input safety policy."
        ),
        *,
        rule: str | None = None,
    ) -> None:
        super().__init__(
            message,
            code="GUARDRAIL_INPUT_BLOCKED",
        )
        self.rule = rule


class GuardrailProviderError(GuardrailError):
    """
    Raised when the underlying guardrail provider fails.
    """

    def __init__(
        self,
        message: str = "Guardrail provider failed.",
    ) -> None:
        super().__init__(
            message,
            code="GUARDRAIL_PROVIDER_ERROR",
        )

class GuardrailConfigurationError(GuardrailError):
    """
    Raised when the guardrail configuration is invalid or missing.
    """

    def __init__(
        self,
        message: str = "Guardrail configuration error.",
    ) -> None:
        super().__init__(
            message,
            code="GUARDRAIL_CONFIGURATION_ERROR",
        )