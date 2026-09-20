"""Tenant isolation and queue behaviour for the agent action repository."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from packages.database.models import Organization, Tenant, User
from packages.database.models.enums import AgentActionStatus, AgentActionType
from packages.database.repositories.agent_action_repository import (
    AgentActionRepository,
)


@pytest_asyncio.fixture
async def other_tenant(async_session):
    """A second tenant, to prove the first one's rows are unreachable."""

    tenant = Tenant(name="Other Co", subdomain=f"other-{uuid4().hex[:8]}")
    async_session.add(tenant)
    await async_session.flush()

    org = Organization(
        tenant_id=tenant.id,
        name="Other Org",
        subdomain=f"other-org-{uuid4().hex[:8]}",
    )
    async_session.add(org)
    await async_session.flush()

    user = User(
        tenant_id=tenant.id,
        org_id=org.id,
        email=f"other-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        role="ADMIN",
    )
    async_session.add(user)
    await async_session.flush()

    return tenant, org, user


def _payload() -> dict:
    return {"title": "Follow up with Acme", "assigned_to_user_id": str(uuid4())}


@pytest.mark.asyncio
async def test_create_forces_the_repository_tenant(
    async_session,
    tenant,
    organization,
    user,
):
    """BaseRepository owns tenant_id; a caller cannot set another tenant's."""

    repo = AgentActionRepository(session=async_session, tenant_id=tenant.id)

    action = await repo.create(
        tenant_id=uuid4(),  # ignored on purpose
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_TASK.value,
        payload=_payload(),
    )

    assert action.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_another_tenant_cannot_read_the_action(
    async_session,
    tenant,
    organization,
    user,
    other_tenant,
):
    repo = AgentActionRepository(session=async_session, tenant_id=tenant.id)

    action = await repo.create(
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_TASK.value,
        payload=_payload(),
    )

    intruder_tenant, _, _ = other_tenant
    intruder = AgentActionRepository(
        session=async_session,
        tenant_id=intruder_tenant.id,
    )

    intruder_org = other_tenant[1]

    assert await intruder.get_by_id(action.id) is None
    assert await intruder.get_for_org(action.id, intruder_org.id) is None
    assert await intruder.claim_pending(action.id, intruder_org.id) is None
    assert await intruder.list_pending() == []


@pytest.mark.asyncio
async def test_another_tenant_cannot_update_the_action(
    async_session,
    tenant,
    organization,
    user,
    other_tenant,
):
    repo = AgentActionRepository(session=async_session, tenant_id=tenant.id)

    action = await repo.create(
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_TASK.value,
        payload=_payload(),
    )

    intruder_tenant, _, _ = other_tenant
    intruder = AgentActionRepository(
        session=async_session,
        tenant_id=intruder_tenant.id,
    )

    assert await intruder.update(action.id, status="APPROVED") is None

    await async_session.refresh(action)
    assert action.status == AgentActionStatus.PENDING.value


@pytest.mark.asyncio
async def test_list_pending_excludes_decided_actions(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AgentActionRepository(session=async_session, tenant_id=tenant.id)

    pending = await repo.create(
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_TASK.value,
        payload=_payload(),
    )

    rejected = await repo.create(
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_CONTACT.value,
        payload={"first_name": "A", "last_name": "B", "company_id": str(uuid4())},
    )
    await repo.update(rejected.id, status=AgentActionStatus.REJECTED.value)

    ids = [a.id for a in await repo.list_pending()]

    assert pending.id in ids
    assert rejected.id not in ids


@pytest.mark.asyncio
async def test_claim_pending_returns_none_once_decided(
    async_session,
    tenant,
    organization,
    user,
):
    """The guard that stops a second approval executing the mutation twice."""

    repo = AgentActionRepository(session=async_session, tenant_id=tenant.id)

    action = await repo.create(
        org_id=organization.id,
        proposed_by_user_id=user.id,
        action_type=AgentActionType.CREATE_TASK.value,
        payload=_payload(),
    )

    assert await repo.claim_pending(action.id, organization.id) is not None

    await repo.update(action.id, status=AgentActionStatus.APPROVED.value)

    assert await repo.claim_pending(action.id, organization.id) is None
