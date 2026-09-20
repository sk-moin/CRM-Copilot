"""
Schemas for Guardrails API.
"""

from pydantic import BaseModel, Field


class GuardrailGenerateRequest(BaseModel):
    """Request to execute a guarded generation."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message.",
    )


class GuardrailGenerateResponse(BaseModel):
    """Guardrail response."""

    response: str

    provider: str

    initialized: bool