from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailAction(str, Enum):
    """Action taken after evaluating content with a guardrail."""

    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"


class OutputGuardrailResult(BaseModel):
    """Result of evaluating an LLM-generated response."""

    allowed: bool = Field(
        ...,
        description="Whether the generated response is safe to return.",
    )

    content: str = Field(
        ...,
        description="The final content to return to the user.",
    )

    action: GuardrailAction = Field(
        ...,
        description="Action taken by the output guardrail.",
    )

    reason: str | None = Field(
        default=None,
        description="Reason for blocking or modifying the response.",
    )

    violations: list[str] = Field(
        default_factory=list,
        description="Guardrail violations detected in the response.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional guardrail evaluation metadata.",
    )