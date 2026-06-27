"""Pydantic schemas for Audit APIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Audit log returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    org_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None

    entity_type: str
    entity_id: uuid.UUID

    action: str

    before_values: Optional[dict[str, Any]] = None
    after_values: Optional[dict[str, Any]] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    actor_type: Optional[str] = None

    correlation_id: Optional[uuid.UUID] = None
    event_metadata: Optional[dict[str, Any]] = None

    created_at: datetime

    @classmethod
    def from_model(cls, audit) -> "AuditLogResponse":
        """Build a response model from an AuditLog ORM object."""

        return cls(
            id=audit.id,
            tenant_id=audit.tenant_id,
            org_id=audit.org_id,
            user_id=audit.user_id,
            entity_type=audit.entity_type,
            entity_id=audit.entity_id,
            action=(
                audit.action.value
                if hasattr(audit.action, "value")
                else str(audit.action)
            ),
            before_values=audit.before_values,
            after_values=audit.after_values,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
            actor_type=audit.actor_type,
            correlation_id=audit.correlation_id,
            event_metadata=audit.event_metadata,
            created_at=audit.created_at,
        )


class TimelineResponse(BaseModel):
    """Paginated audit timeline."""

    entity_type: str
    entity_id: str

    events: list[AuditLogResponse]

    count: int
    page: int
    page_size: int