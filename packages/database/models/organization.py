"""Organization model – belongs to a Tenant."""

from __future__ import annotations

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from packages.database.models.base import Base
from packages.database.models.tenant import Tenant


class Organization(Base):
    """Organization under a tenant."""

    __tablename__ = "organization"

    id: PGUUID = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Primary key",
    )
    tenant_id: PGUUID = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → tenant.id – enforces tenant isolation",
    )
    name: str = Column(String, nullable=False, comment="Organization name")
    # New – unique subdomain required by Spec 001.
    subdomain: str = Column(
        String,
        nullable=False,
        unique=True,
        comment="Unique organization subdomain",
    )
    domain: str | None = Column(
        String, nullable=True, comment="Optional custom domain for the org"
    )
    created_at: datetime.datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of organization creation",
    )

    # Relationships
    tenant = relationship("Tenant", backref="organizations", lazy="joined")
