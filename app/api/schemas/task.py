"""Pydantic v2 schemas for the ``Task`` entity.

All response schemas include ``id``, ``created_at`` and ``updated_at`` fields.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Base schema – shared fields for create/read operations
# ---------------------------------------------------------------------------

class TaskBase(BaseModel):
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Longer description of the task (optional)")
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"] = Field(
        "PENDING", description="Current status of the task"
    )
    priority: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        "MEDIUM", description="Task priority level"
    )
    due_date: Optional[date] = Field(None, description="Optional task due date")
    assigned_to_user_id: UUID = Field(
        ..., description="UUID of the user responsible for the task"
    )
    entity_type: Optional[Literal["company", "contact", "opportunity"]] = Field(
        None, description="Entity type this task is attached to"
    )
    entity_id: Optional[UUID] = Field(
        None, description="PK of the attached entity – no FK enforced"
    )

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Create schema – used for POST /tasks
# ---------------------------------------------------------------------------

class TaskCreate(TaskBase):
    """Fields required to create a Task (PK and tenant omitted)."""
    pass

# ---------------------------------------------------------------------------
# Update schema – all fields optional for PATCH /tasks/{id}
# ---------------------------------------------------------------------------

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Task title – required")
    description: Optional[str] = Field(
        None, description="Longer description of the task (optional)"
    )
    status: Optional[Literal["PENDING", "IN_PROGRESS", "COMPLETED"]] = Field(
        None, description="Current status of the task"
    )
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        None, description="Task priority level"
    )
    due_date: Optional[date] = Field(None, description="Optional task due date")
    assigned_to_user_id: Optional[UUID] = Field(
        None, description="UUID of the user responsible for the task"
    )
    entity_type: Optional[Literal["company", "contact", "opportunity"]] = Field(
        None, description="Entity type this task is attached to"
    )
    entity_id: Optional[UUID] = Field(
        None, description="PK of the attached entity – no FK enforced"
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def check_entity_pair(self):
        """Validate that entity_type and entity_id are both set or both omitted."""
        if (self.entity_type is None) ^ (self.entity_id is None):
            raise ValueError(
                "entity_type and entity_id must be both set or both omitted"
            )
        return self

# ---------------------------------------------------------------------------
# Response schema – returned by GET endpoints (ORM serialization enabled)
# ---------------------------------------------------------------------------

class TaskResponse(TaskBase):
    id: UUID = Field(..., description="Primary key (UUID) of the task")
    created_at: datetime = Field(..., description="Timestamp of task creation")
    updated_at: datetime = Field(..., description="Timestamp of last task update")