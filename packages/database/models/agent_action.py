"""AgentAction model - a CRM mutation the agent proposed, awaiting a human.

The point of this table is that the agent never writes to the CRM directly. It
records an intention here; a person approves it; only then does the mutation
run. Feature 003's audit log records every transition, with `actor_type`
separating the agent's proposal from the human's decision.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from packages.database.models.base import Base


class AgentAction(Base):
    """A proposed CRM mutation and the record of what was decided about it."""

    __tablename__ = "agent_action"

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
        comment="Tenant isolation. Every query filters on this.",
    )

    org_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="SET NULL"),
        nullable=True,
        comment="Where the proposal was made. Null once the conversation goes.",
    )

    proposed_by_user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="Whose turn produced the proposal. Not the approver.",
    )

    action_type = Column(
        Enum(
            "CREATE_TASK",
            "UPDATE_TASK_STATUS",
            "CREATE_CONTACT",
            "UPDATE_CONTACT",
            "UPDATE_OPPORTUNITY_STAGE",
            name="agent_action_type",
        ),
        nullable=False,
    )

    payload = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Validated against a per-type schema before execution.",
    )

    reason = Column(
        Text,
        nullable=True,
        comment="The agent's stated rationale, shown to the approver.",
    )

    status = Column(
        Enum(
            "PENDING",
            "APPROVED",
            "REJECTED",
            "EXECUTED",
            "FAILED",
            name="agent_action_status",
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    decided_by_user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        comment="The human who approved or rejected. Never the agent.",
    )

    decided_at = Column(DateTime(timezone=True), nullable=True)

    decision_reason = Column(Text, nullable=True)

    executed_at = Column(DateTime(timezone=True), nullable=True)

    result_entity_type = Column(String, nullable=True)

    result_entity_id = Column(PGUUID(as_uuid=True), nullable=True)

    error_message = Column(Text, nullable=True)

    correlation_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
        server_default=func.gen_random_uuid(),
        comment="Joins the proposal and its outcome in the audit log.",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # Listing a tenant's pending actions is the hot query.
        Index("ix_agent_action_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentAction id={self.id} type={self.action_type} "
            f"status={self.status}>"
        )
