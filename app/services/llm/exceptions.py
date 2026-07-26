"""Exceptions for Prompt Management."""


class PromptError(Exception):
    """Base exception for all prompt-related errors."""


class PromptNotFoundError(PromptError):
    """Raised when a prompt cannot be found."""

    def __init__(self, prompt_name: str) -> None:
        super().__init__(f"Prompt '{prompt_name}' was not found.")


class PromptVersionNotFoundError(PromptError):
    """Raised when a prompt has no available versions."""

    def __init__(self, prompt_name: str) -> None:
        super().__init__(
            f"No versions found for prompt '{prompt_name}'."
        )


class PromptRenderError(PromptError):
    """Raised when prompt rendering fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class PromptValidationError(PromptError):
    """Raised when a prompt template is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class PromptCacheError(PromptError):
    """Raised when a prompt cache operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)