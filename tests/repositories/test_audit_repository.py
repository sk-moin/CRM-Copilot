import uuid

import pytest

from packages.database.models import AuditAction
from packages.database.repositories.audit_repository import AuditRepository


pytestmark = pytest.mark.asyncio


async def test_create_audit_log(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    audit = await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=uuid.uuid4(),
        after_values={"name": "Acme"},
    )

    assert audit.id is not None
    assert audit.tenant_id == tenant.id
    assert audit.org_id == organization.id
    assert audit.user_id == user.id
    assert audit.action == AuditAction.CREATE
    assert audit.entity_type == "company"
    assert audit.after_values["name"] == "Acme"


async def test_create_requires_required_fields(
    async_session,
    tenant,
):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    with pytest.raises(ValueError):
        await repo.create(
            entity_type="company",
            entity_id=uuid.uuid4(),
        )


async def test_list_for_entity(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    entity_id = uuid.uuid4()

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=entity_id,
    )

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="company",
        entity_id=entity_id,
    )

    logs = await repo.list_for_entity(
        entity_type="company",
        entity_id=entity_id,
    )

    assert len(logs) == 2
    assert all(log.entity_id == entity_id for log in logs)


async def test_list_for_user(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=uuid.uuid4(),
    )

    logs = await repo.list_for_user(
        user_id=user.id,
    )

    assert len(logs) == 1
    assert logs[0].user_id == user.id


async def test_list_for_tenant(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session, tenant_id=tenant.id)

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=uuid.uuid4(),
    )

    logs = await repo.list_for_tenant()

    assert len(logs) >= 1
    assert all(log.tenant_id == tenant.id for log in logs)


async def test_list_by_correlation_id(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session, tenant_id=tenant.id)

    correlation_id = uuid.uuid4()

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=uuid.uuid4(),
        correlation_id=correlation_id,
    )

    logs = await repo.list_by_correlation_id(
        correlation_id=correlation_id,
    )

    assert len(logs) == 1
    assert logs[0].correlation_id == correlation_id


async def test_count_for_entity(
    async_session,
    tenant,
    organization,
    user,
):
    repo = AuditRepository(session=async_session, tenant_id=tenant.id)

    entity_id = uuid.uuid4()

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.CREATE,
        entity_type="company",
        entity_id=entity_id,
    )

    await repo.create(
        org_id=organization.id,
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="company",
        entity_id=entity_id,
    )

    count = await repo.count_for_entity(
        entity_type="company",
        entity_id=entity_id,
    )

    assert count == 2


async def test_update_not_allowed(async_session,tenant):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    with pytest.raises(NotImplementedError):
        await repo.update()


async def test_delete_not_allowed(async_session,tenant):
    repo = AuditRepository(session=async_session,tenant_id=tenant.id)

    with pytest.raises(NotImplementedError):
        await repo.delete()