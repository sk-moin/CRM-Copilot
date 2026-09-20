"""Per-type payload schemas for agent-proposed CRM actions.

Every proposal is validated against one of these before it is stored and again
before it executes. The schemas are strict: an unexpected key is a rejected
proposal, not a silently-ignored one. A model writing this JSON is an untrusted
source, and the whole point of the approval layer is that nothing reaches the
CRM unexamined.
"""

from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.database.models.enums import AgentActionType


class _StrictPayload(BaseModel):
    """Reject unknown fields rather than dropping them."""

    model_config = ConfigDict(extra="forbid")


# Mirrors the PostgreSQL enums. Validating here means an out-of-range value is
# a refused proposal, not a database error raised mid-transaction: "DONE" is
# the most natural status an LLM emits for a task, and it is not a member.
TaskStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED"]
TaskPriority = Literal["LOW", "MEDIUM", "HIGH"]
OpportunityStage = Literal[
    "LEAD", "QUALIFIED", "PROPOSAL", "NEGOTIATION", "WON", "LOST"
]


class CreateTaskPayload(_StrictPayload):
    title: str = Field(min_length=1, max_length=255)
    assigned_to_user_id: UUID
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: TaskPriority = "MEDIUM"
    status: TaskStatus = "PENDING"
    entity_type: Optional[str] = Field(default=None, max_length=64)
    entity_id: Optional[UUID] = None


class UpdateTaskStatusPayload(_StrictPayload):
    task_id: UUID
    status: TaskStatus


class CreateContactPayload(_StrictPayload):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    company_id: UUID
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=64)
    job_title: Optional[str] = Field(default=None, max_length=255)


class UpdateContactPayload(_StrictPayload):
    contact_id: UUID
    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=64)
    job_title: Optional[str] = Field(default=None, max_length=255)


class UpdateOpportunityStagePayload(_StrictPayload):
    opportunity_id: UUID
    stage: OpportunityStage


PAYLOAD_SCHEMAS: dict[AgentActionType, type[_StrictPayload]] = {
    AgentActionType.CREATE_TASK: CreateTaskPayload,
    AgentActionType.UPDATE_TASK_STATUS: UpdateTaskStatusPayload,
    AgentActionType.CREATE_CONTACT: CreateContactPayload,
    AgentActionType.UPDATE_CONTACT: UpdateContactPayload,
    AgentActionType.UPDATE_OPPORTUNITY_STAGE: UpdateOpportunityStagePayload,
}
"""Literal mapping. A payload never selects its own schema by name."""


def schema_for(action_type: AgentActionType) -> type[_StrictPayload]:
    """Return the schema for a type, or raise for an unsupported one."""

    schema = PAYLOAD_SCHEMAS.get(action_type)

    if schema is None:
        raise KeyError(f"No payload schema for action type {action_type!r}.")

    return schema
