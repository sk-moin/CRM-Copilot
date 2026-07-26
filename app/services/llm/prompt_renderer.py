"""Prompt rendering utilities."""

from __future__ import annotations

from typing import Any

from jinja2 import (
    Environment,
    StrictUndefined,
    TemplateError,
)


class PromptRenderError(Exception):
    """Raised when prompt rendering fails."""


class PromptRenderer:
    """
    Jinja2 prompt rendering utility.

    Responsible only for rendering and validating templates.
    """

    def __init__(self) -> None:
        self._environment = Environment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        template: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a prompt template.

        Args:
            template:
                Jinja2 template.

            variables:
                Variables passed into the template.

        Returns:
            Rendered prompt string.

        Raises:
            PromptRenderError:
                If rendering fails.
        """

        variables = variables or {}

        try:
            compiled = self._environment.from_string(
                template,
            )

            return compiled.render(
                **variables,
            )

        except TemplateError as exc:
            raise PromptRenderError(
                f"Failed to render prompt: {exc}"
            ) from exc

    def validate(
        self,
        template: str,
        variables: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validate that a template can be rendered.

        Returns:
            True if rendering succeeds.

        Raises:
            PromptRenderError
        """

        self.render(
            template,
            variables,
        )

        return True