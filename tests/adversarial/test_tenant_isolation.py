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
        subdomain="org-a",
        domain="org-a.local",
    )
    async_session.add(org_a)
    await async_session.flush()
    user_a = User(
        tenant_id=tenant_a.id,
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
        subdomain="org-b",
        domain="org-b.local",
    )
    async_session.add(org_b)
    await async_session.flush()
    user_b = User(
        tenant_id=tenant_b.id,
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


# --------------------------------------------------------------------------- #
# Agent actions (feature 010)
# --------------------------------------------------------------------------- #


async def _seed_tenant(async_session, label: str):
    """A tenant with an organization and a user, for isolation tests."""

    from uuid import uuid4

    tenant = Tenant(name=f"{label} Co", subdomain=f"{label}-{uuid4().hex[:8]}")
    async_session.add(tenant)
    await async_session.flush()

    org = Organization(
        tenant_id=tenant.id,
        name=f"{label} Org",
        subdomain=f"{label}-org-{uuid4().hex[:8]}",
    )
    async_session.add(org)
    await async_session.flush()

    user = User(
        tenant_id=tenant.id,
        org_id=org.id,
        email=f"{label}-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        role="ADMIN",
    )
    async_session.add(user)
    await async_session.flush()

    return tenant, org, user


@pytest.mark.asyncio
async def test_agent_action_is_invisible_across_tenants(async_session):
    """An approval queue that leaks across tenants would be a serious breach:
    it exposes proposed mutations and lets an outsider execute them."""

    from app.services.agent_action_service import (
        ActionNotFoundError,
        AgentActionService,
    )

    _, _, user_a = await _seed_tenant(async_session, "alpha")
    _, _, user_b = await _seed_tenant(async_session, "beta")

    service_a = AgentActionService(session=async_session, current_user=user_a)
    service_b = AgentActionService(session=async_session, current_user=user_b)

    action = await service_a.propose(
        action_type="CREATE_TASK",
        payload={"title": "Alpha only", "assigned_to_user_id": str(user_a.id)},
    )

    # Not listable.
    assert action.id not in [a.id for a in await service_b.list_actions()]

    # Not readable.
    with pytest.raises(ActionNotFoundError):
        await service_b.get_action(action.id)

    # Not approvable: the outsider must not be able to execute the mutation.
    with pytest.raises(ActionNotFoundError):
        await service_b.approve(action.id)

    # Not rejectable either.
    with pytest.raises(ActionNotFoundError):
        await service_b.reject(action.id)

    # Still pending and untouched for its owner.
    owned = await service_a.get_action(action.id)
    assert owned.status == "PENDING"
    assert owned.decided_by_user_id is None


@pytest.mark.asyncio
async def test_agent_action_does_not_cross_org_within_a_tenant(async_session):
    """Same tenant, different org, is still a boundary.

    list_actions filtered by org from the start, which made the scoping look
    complete. get/approve/reject did not: another org's user could read an
    action, approve it, and because the executor stamps the CRM row with the
    approver's org, the created record landed in the wrong org entirely --
    invisible to the org that proposed it, and with the AgentAction row and
    the CRM row disagreeing about where it belonged.
    """

    from uuid import uuid4

    from app.services.agent_action_service import (
        ActionNotFoundError,
        AgentActionService,
    )

    tenant = Tenant(name="Shared Co", subdomain=f"shared-{uuid4().hex[:8]}")
    async_session.add(tenant)
    await async_session.flush()

    users = []
    for label in ("orga", "orgb"):
        org = Organization(
            tenant_id=tenant.id,
            name=label,
            subdomain=f"{label}-{uuid4().hex[:8]}",
        )
        async_session.add(org)
        await async_session.flush()

        user = User(
            tenant_id=tenant.id,
            org_id=org.id,
            email=f"{label}-{uuid4().hex[:8]}@example.com",
            password_hash="x",
            role="ADMIN",
        )
        async_session.add(user)
        await async_session.flush()
        users.append(user)

    user_a, user_b = users

    service_a = AgentActionService(session=async_session, current_user=user_a)
    service_b = AgentActionService(session=async_session, current_user=user_b)

    action = await service_a.propose(
        action_type="CREATE_TASK",
        payload={"title": "org A work", "assigned_to_user_id": str(user_a.id)},
    )

    assert action.id not in [a.id for a in await service_b.list_actions()]

    with pytest.raises(ActionNotFoundError):
        await service_b.get_action(action.id)

    with pytest.raises(ActionNotFoundError):
        await service_b.approve(action.id)

    with pytest.raises(ActionNotFoundError):
        await service_b.reject(action.id)

    still = await service_a.get_action(action.id)
    assert still.status == "PENDING"
