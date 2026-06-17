"""Unit tests for the core DB models.

These tests verify that the ORM relationships work as expected and that the
columns store the data we provide. They run against the local Postgres instance
started by docker‑compose.
"""

import pytest
from sqlalchemy import select

from packages.database.models import Tenant, Organization, User
from packages.database.repositories.base_repository import BaseRepository

@pytest.mark.asyncio
async def test_create_and_relationships(async_session):
    # --- create a tenant ---
    tenant = Tenant(name="Acme Corp", subdomain="acme")
    async_session.add(tenant)
    await async_session.flush()  # assign PK without committing

    # --- create an organization belonging to the tenant ---
    org = Organization(
        tenant_id=tenant.id,
        name="Acme Sales",
        subdomain="acme-sales",
        domain="sales.acme.com",
    )
    async_session.add(org)
    await async_session.flush()

    # --- create a user belonging to the organization ---
    user = User(
        org_id=org.id,
        email="alice@example.com",
        password_hash="fakehash",
        role="MEMBER",
    )
    async_session.add(user)
    await async_session.commit()

    # Refresh objects from the DB to test relationships
    await async_session.refresh(tenant)
    await async_session.refresh(org)
    await async_session.refresh(user)

    # Relationship checks
    assert org.tenant is tenant
    assert user.organization is org
    # The indirect tenant relationship via organization should also resolve
    assert user.organization.tenant is tenant

    # Column value checks
    assert tenant.name == "Acme Corp"
    assert tenant.subdomain == "acme"
    assert org.name == "Acme Sales"
    assert org.domain == "sales.acme.com"
    assert user.email == "alice@example.com"
    assert user.role == "MEMBER"
