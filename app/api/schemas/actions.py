"""Schemas for the agent action approval API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentActionResponse(BaseModel):
    """A proposed action and whatever has been decided about it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    org_id: UUID

    conversation_id: Optional[UUID] = None
    proposed_by_user_id: UUID

    action_type: str
    payload: dict[str, Any]
    reason: Optional[str] = None

    status: str

    decided_by_user_id: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    decision_reason: Optional[str] = None

    executed_at: Optional[datetime] = None
    result_entity_type: Optional[str] = None
    result_entity_id: Optional[UUID] = None

    error_message: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class AgentActionListResponse(BaseModel):
    items: list[AgentActionResponse]
    total: int


class ActionDecisionRequest(BaseModel):
    """Optional note recorded with an approval or rejection."""

    reason: Optional[str] = Field(default=None, max_length=2000)
