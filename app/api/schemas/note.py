"""Pydantic v2 schemas for the ``Note`` entity.

All response schemas include ``id``, ``created_at`` and ``updated_at`` fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Base schema – shared fields for create/read operations
# ---------------------------------------------------------------------------

class NoteBase(BaseModel):
    content: str = Field(..., description="Full text content of the note")
    entity_type: Literal["company", "contact", "opportunity"] = Field(
        ..., description="Entity type this note is attached to"
    )
    entity_id: UUID = Field(..., description="PK of the attached entity – no FK enforced")

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Create schema – used for POST /notes
# ---------------------------------------------------------------------------

class NoteCreate(NoteBase):
    """Fields required to create a Note (PK and tenant omitted)."""
    pass

# ---------------------------------------------------------------------------
# Update schema – all fields optional for PATCH /notes/{id}
# ---------------------------------------------------------------------------

class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Full text content of the note")
    entity_type: Optional[Literal["company", "contact", "opportunity"]] = Field(
        None, description="Entity type this note is attached to"
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

class NoteResponse(NoteBase):
    id: UUID = Field(..., description="Primary key (UUID) of the note")
    created_at: datetime = Field(..., description="Timestamp of note creation")
    updated_at: datetime = Field(..., description="Timestamp of last note update")