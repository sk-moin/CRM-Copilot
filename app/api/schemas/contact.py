"""Pydantic v2 schemas for the ``Contact`` entity.

All response schemas include ``id``, ``created_at`` and ``updated_at`` fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Base schema – shared fields for create/read operations
# ---------------------------------------------------------------------------

class ContactBase(BaseModel):
    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    job_title: Optional[str] = Field(None, description="Contact job title")
    company_id: UUID = Field(..., description="UUID of the associated company")

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Create schema – used for POST /contacts
# ---------------------------------------------------------------------------

class ContactCreate(ContactBase):
    """Fields required to create a Contact (PK and tenant omitted)."""
    pass

# ---------------------------------------------------------------------------
# Update schema – all fields optional for PATCH /contacts/{id}
# ---------------------------------------------------------------------------

class ContactUpdate(BaseModel):
    first_name: Optional[str] = Field(None, description="Contact first name")
    last_name: Optional[str] = Field(None, description="Contact last name")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    job_title: Optional[str] = Field(None, description="Contact job title")
    company_id: Optional[UUID] = Field(None, description="UUID of the associated company")

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Response schema – returned by GET endpoints (ORM serialization enabled)
# ---------------------------------------------------------------------------

class ContactResponse(ContactBase):
    id: UUID = Field(..., description="Primary key (UUID) of the contact")
    created_at: datetime = Field(..., description="Timestamp of contact creation")
    updated_at: datetime = Field(..., description="Timestamp of last contact update")