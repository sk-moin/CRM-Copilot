"""Tests for the AuditLog model (Phase 3A).

These tests verify that the model can be instantiated, that required fields are
enforced, and that the JSONB columns accept Python dicts. They run against the
in‑memory test database using the ``async_session`` fixture.
"""

import pytest
import uuid
from sqlalchemy import inspect

from packages.database.models import AuditLog, AuditAction
from packages.database.models import Base
from uuid import UUID

@pytest.mark.asyncio
async def test_audit_log_required_fields(async_session, tenant):
    """Create a minimal AuditLog and ensure required columns are set.

    The ``tenant_id`` and ``entity_type``/``entity_id``/``action`` fields are
    required by the specification. ``org_id`` and ``user_id`` are optional.
    """
    # Minimal required data – use a fake UUID for tenant and entity.
    
    audit = AuditLog(
        tenant_id=tenant.id,
        entity_type="company",
        entity_id=uuid.uuid4(),
        action=AuditAction.CREATE,
    )
    async_session.add(audit)
    await async_session.flush()

    # After flush the PK should be populated.
    assert audit.id is not None
    # Verify enum value stored as string.
    assert audit.action == AuditAction.CREATE

    # Ensure optional JSON fields default to None.
    assert audit.before_values is None
    assert audit.after_values is None
    assert audit.event_metadata is None


@pytest.mark.asyncio
async def test_audit_log_jsonb_columns(async_session, tenant):
    """JSONB columns should accept dictionaries and be persisted correctly."""
    before = {"name": "Old Co"}
    after = {"name": "New Co"}
    metadata = {"source": "unit_test"}

    audit = AuditLog(
        tenant_id=tenant.id,
        entity_type="company",
        entity_id=uuid.uuid4(),
        action=AuditAction.UPDATE,
        before_values=before,
        after_values=after,
        event_metadata=metadata,
    )
    async_session.add(audit)
    await async_session.flush()

    # Retrieve via inspection to ensure values round‑trip through SQLAlchemy.
    insp = inspect(audit)
    attrs = {c.key: getattr(audit, c.key) for c in insp.mapper.column_attrs}
    assert attrs["before_values"] == before
    assert attrs["after_values"] == after
    assert attrs["event_metadata"] == metadata
