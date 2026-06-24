"""User model – belongs to an Organization (and indirectly to a Tenant)."""

from __future__ import annotations

import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from packages.database.models.base import Base
from packages.database.models.organization import Organization


class User(Base):
    __tablename__ = "user"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Direct tenant ownership",
    )

    org_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = Column(
        String,
        nullable=False,
    )

    role = Column(
        Enum(
            "OWNER",
            "ADMIN",
            "MANAGER",
            "MEMBER",
            name="user_role",
        ),
        nullable=False,
        default="MEMBER",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant = relationship(
        "Tenant",
        backref="users",
        lazy="joined",
    )

    organization = relationship(
        "Organization",
        backref="users",
        lazy="joined",
    )