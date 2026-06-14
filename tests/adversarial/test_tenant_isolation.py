"""Adversarial tests for tenant isolation.

The goal is to ensure that a repository scoped to one tenant cannot see or
manipulate data belonging to another tenant. This matches the requirement in
spec 000 (adversarial test)."""

import pytest
from packages.database.models import Tenant, Organization, User
from packages.database.repositories.base_repository import BaseRepository

class UserRepository(BaseRepository):
    model = User
@pytest.mark.asyncio
async def test_tenant_isolation_via_repository(async_session):
    # --- Tenant A ---
    tenant_a = Tenant(name="Tenant A", subdomain="a")
    async_session.add(tenant_a)
    await async_session.flush()
    org_a = Organization(
        tenant_id=tenant_a.id,
        name="Org A",
        domain="org-a.local",
    )
    async_session.add(org_a)
    await async_session.flush()
    user_a = User(
        org_id=org_a.id,
        email="a_user@example.com",
        password_hash="hash-a",
        role="OWNER",
    )
    async_session.add(user_a)
    await async_session.flush()

    # --- Tenant B ---
    tenant_b = Tenant(name="Tenant B", subdomain="b")
    async_session.add(tenant_b)
    await async_session.flush()
    org_b = Organization(
        tenant_id=tenant_b.id,
        name="Org B",
        domain="org-b.local",
    )
    async_session.add(org_b)
    await async_session.flush()
    user_b = User(
        org_id=org_b.id,
        email="b_user@example.com",
        password_hash="hash-b",
        role="ADMIN",
    )
    async_session.add(user_b)
    await async_session.flush()


    # Scoped repository for Tenant A
    repo_a = UserRepository(async_session, tenant_id=tenant_a.id)

    # get_by_id for B's user should return None (tenant isolation)
    fetched_b_user = await repo_a.get_by_id(user_b.id)
    assert fetched_b_user is None

    # list() scoped to Tenant A should not include B's user
    users_a = await repo_a.list()
    # Collect only email addresses for easier assertion
    emails_a = {u.email for u in users_a}
    assert "b_user@example.com" not in emails_a
    # Ensure that Tenant A's own user is present
    assert "a_user@example.com" in emails_a
