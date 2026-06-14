"""User model – belongs to an Organization (and indirectly to a Tenant)."""

from __future__ import annotations

import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from packages.database.models.base import Base
from packages.database.models.organization import Organization


class User(Base):
    """User account belonging to an organization."""

    __tablename__ = "user"

    id: PGUUID = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Primary key",
    )
    org_id: PGUUID = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → organization.id – indirect tenant link",
    )
    email: str = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
        comment="User email address – unique across all tenants",
    )
    password_hash: str = Column(
        String, nullable=False, comment="Bcrypt hash of the user's password"
    )
    role: str = Column(
        Enum(
            "OWNER",
            "ADMIN",
            "MANAGER",
            "MEMBER",
            name="user_role",
        ),
        nullable=False,
        default="MEMBER",
        comment="Role within the organization (enum‑like)",
    )
    created_at: datetime.datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of user creation",
    )

    # Relationships
    organization = relationship(
        "Organization", backref="users", lazy="joined"
    )
