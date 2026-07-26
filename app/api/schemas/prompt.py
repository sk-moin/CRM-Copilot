"""Pydantic schemas for Prompt Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.database.models.prompt import PromptCategory


# ---------------------------------------------------------------------
# Prompt Version Schemas
# ---------------------------------------------------------------------


class PromptVersionCreate(BaseModel):
    """Schema for creating a new prompt version."""

    template: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)

    model_name: str | None = None
    temperature: float = 0.2
    top_p: float = 1.0
    max_tokens: int | None = None

    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    prompt_id: UUID

    version: int
    template: str

    variables: list[str]

    model_name: str | None = Field(
        validation_alias="llm_model",
    )

    temperature: float
    top_p: float
    max_tokens: int | None

    response_format: dict[str, Any] | None

    metadata: dict[str, Any] = Field(
        validation_alias="config",
        default_factory=dict,
    )

    created_by: UUID | None
    created_at: datetime


# ---------------------------------------------------------------------
# Prompt Schemas
# ---------------------------------------------------------------------


class PromptCreate(BaseModel):
    """Create a prompt."""


    name: str = Field(..., min_length=1, max_length=100)

    category: PromptCategory = PromptCategory.SYSTEM

    description: str | None = None


class PromptUpdate(BaseModel):
    """Update prompt metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=100)

    category: PromptCategory | None = None

    description: str | None = None

    active_version_id: UUID | None = None


class PromptResponse(BaseModel):
    """Prompt response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    tenant_id: UUID
    org_id: UUID

    name: str
    category: PromptCategory

    description: str | None

    active_version_id: UUID | None

    created_at: datetime
    updated_at: datetime


class PromptDetailResponse(PromptResponse):
    """Detailed prompt response including versions."""

    versions: list[PromptVersionResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Prompt Rendering
# ---------------------------------------------------------------------


class PromptRenderRequest(BaseModel):
    """Request to render a prompt."""

    variables: dict[str, Any] = Field(default_factory=dict)


class PromptRenderResponse(BaseModel):
    """Rendered prompt."""

    prompt: str