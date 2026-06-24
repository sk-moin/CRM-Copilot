#app/api/schemas/opportunity.py
"""Pydantic v2 schemas for the ``Opportunity`` entity.

All response schemas include ``id``, ``created_at`` and ``updated_at`` fields.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Base schema – shared fields for create/read operations
# ---------------------------------------------------------------------------

class OpportunityBase(BaseModel):
    title: str = Field(..., description="Opportunity title")
    stage: Literal[
        "LEAD",
        "QUALIFIED",
        "PROPOSAL",
        "NEGOTIATION",
        "WON",
        "LOST",
    ] = Field(..., description="Current stage in the sales pipeline")
    probability: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Probability (0‑100) that the opportunity will close",
    )
    value: Optional[Decimal] = Field(None, description="Monetary value of the opportunity")
    expected_close_date: Optional[date] = Field(
        None, description="Expected close date (optional)"
    )
    company_id: UUID = Field(..., description="UUID of the associated company")
    owner_user_id: UUID = Field(..., description="UUID of the user that owns the opportunity")

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Create schema – used for POST /opportunities
# ---------------------------------------------------------------------------

class OpportunityCreate(OpportunityBase):
    """Fields required to create an Opportunity (PK and tenant omitted)."""
    pass

# ---------------------------------------------------------------------------
# Update schema – all fields optional for PATCH /opportunities/{id}
# ---------------------------------------------------------------------------

class OpportunityUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Opportunity title")
    stage: Optional[Literal[
        "LEAD",
        "QUALIFIED",
        "PROPOSAL",
        "NEGOTIATION",
        "WON",
        "LOST",
    ]] = Field(None, description="Current stage in the sales pipeline")
    probability: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Probability (0‑100) that the opportunity will close",
    )
    value: Optional[Decimal] = Field(None, description="Monetary value of the opportunity")
    expected_close_date: Optional[date] = Field(
        None, description="Expected close date (optional)"
    )
    company_id: Optional[UUID] = Field(None, description="UUID of the associated company")
    owner_user_id: Optional[UUID] = Field(None, description="UUID of the user that owns the opportunity")

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Response schema – returned by GET endpoints (ORM serialization enabled)
# ---------------------------------------------------------------------------

class OpportunityResponse(OpportunityBase):
    id: UUID = Field(..., description="Primary key (UUID) of the opportunity")
    created_at: datetime = Field(..., description="Timestamp of opportunity creation")
    updated_at: datetime = Field(..., description="Timestamp of last opportunity update")