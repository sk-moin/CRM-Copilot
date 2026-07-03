import uuid

import pytest

from app.services.audit_service import AuditService
from packages.database.models import AuditAction


pytestmark = pytest.mark.asyncio


async def test_log_create(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    entity_id = uuid.uuid4()

    audit = await service.log_create(
        entity_type="company",
        entity_id=entity_id,
        after_values={"name": "Acme"},
    )

    assert audit.id is not None
    assert audit.action == AuditAction.CREATE
    assert audit.entity_type == "company"
    assert audit.entity_id == entity_id
    assert audit.user_id == user.id
    assert audit.org_id == organization.id
    assert audit.after_values["name"] == "Acme"


async def test_log_update(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    entity_id = uuid.uuid4()

    audit = await service.log_update(
        entity_type="company",
        entity_id=entity_id,
        before_values={"name": "Old"},
        after_values={"name": "New"},
    )

    assert audit.action == AuditAction.UPDATE
    assert audit.before_values["name"] == "Old"
    assert audit.after_values["name"] == "New"


async def test_log_delete(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    entity_id = uuid.uuid4()

    audit = await service.log_delete(
        entity_type="company",
        entity_id=entity_id,
        before_values={"name": "Acme"},
    )

    assert audit.action == AuditAction.DELETE
    assert audit.before_values["name"] == "Acme"


async def test_get_timeline(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    entity_id = uuid.uuid4()

    await service.log_create(
        entity_type="company",
        entity_id=entity_id,
    )

    await service.log_update(
        entity_type="company",
        entity_id=entity_id,
    )

    timeline = await service.get_timeline(
        entity_type="company",
        entity_id=entity_id,
    )

    assert len(timeline) == 2


async def test_get_user_activity(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    await service.log_create(
        entity_type="company",
        entity_id=uuid.uuid4(),
    )

    activity = await service.get_user_activity(
        user_id=user.id,
    )

    assert len(activity) == 1
    assert activity[0].user_id == user.id


async def test_get_correlation_events(
    async_session,
    tenant,
    organization,
    user,
):
    service = AuditService(
        session=async_session,
        tenant_id=tenant.id,
        current_user=user,
    )

    correlation_id = uuid.uuid4()

    await service.log_create(
        entity_type="company",
        entity_id=uuid.uuid4(),
        correlation_id=correlation_id,
    )

    events = await service.get_correlation_events(
        correlation_id=correlation_id,
    )

    assert len(events) == 1
    assert events[0].correlation_id == correlation_id


def test_build_company_snapshot():
    class DummyCompany:
        id = uuid.uuid4()
        name = "Acme"
        industry = "Software"
        website = "https://acme.com"

    snapshot = AuditService.build_company_snapshot(
        DummyCompany()
    )

    assert snapshot["name"] == "Acme"
    assert snapshot["industry"] == "Software"
    assert snapshot["website"] == "https://acme.com"
    assert isinstance(snapshot["id"], str)


def test_build_contact_snapshot():
    class DummyContact:
        id = uuid.uuid4()
        first_name = "John"
        last_name = "Doe"
        email = "john@example.com"
        company_id = uuid.uuid4()

    snapshot = AuditService.build_contact_snapshot(
        DummyContact()
    )

    assert snapshot["first_name"] == "John"
    assert snapshot["last_name"] == "Doe"
    assert snapshot["email"] == "john@example.com"
    assert isinstance(snapshot["company_id"], str)


def test_build_opportunity_snapshot():
    class DummyOpportunity:
        id = uuid.uuid4()
        title = "Enterprise Deal"
        stage = "LEAD"
        value = 50000

    snapshot = AuditService.build_opportunity_snapshot(
        DummyOpportunity()
    )

    assert snapshot["title"] == "Enterprise Deal"
    assert snapshot["stage"] == "LEAD"
    assert snapshot["value"] == 50000


def test_build_task_snapshot():
    class DummyTask:
        id = uuid.uuid4()
        title = "Call customer"
        status = "PENDING"
        priority = "HIGH"

    snapshot = AuditService.build_task_snapshot(
        DummyTask()
    )

    assert snapshot["title"] == "Call customer"
    assert snapshot["status"] == "PENDING"
    assert snapshot["priority"] == "HIGH"