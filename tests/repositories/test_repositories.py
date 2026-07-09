"""Unit tests for repository safety guardrails."""

import pytest

from packages.database.exceptions import InvalidTenantIdError
from packages.database.models import Tenant
from packages.database.repositories.tenant_repository import TenantRepository
from packages.database.repositories.organization_repository import OrganizationRepository
from packages.database.repositories.user_repository import UserRepository


class DummySession:
    """A dummy session for testing repository instantiation."""
    pass


def test_tenant_repository_rejects_none_tenant_id():
    """TenantRepository should raise InvalidTenantIdError when tenant_id is None."""
    with pytest.raises(InvalidTenantIdError):
        TenantRepository(DummySession(), tenant_id=None)


def test_organization_repository_rejects_none_tenant_id():
    """OrganizationRepository should raise InvalidTenantIdError when tenant_id is None."""
    with pytest.raises(InvalidTenantIdError):
        OrganizationRepository(DummySession(), tenant_id=None)


def test_user_repository_rejects_none_tenant_id():
    """UserRepository should raise InvalidTenantIdError when tenant_id is None."""
    with pytest.raises(InvalidTenantIdError):
        UserRepository(DummySession(), tenant_id=None)


def test_tenant_repository_accepts_valid_tenant_id():
    """TenantRepository should accept a valid tenant_id."""
    # Valid tenant_id can be any non-None value; using a dummy string for test.
    valid_tenant_id = "valid-tenant-id"
    repo = TenantRepository(DummySession(), tenant_id=valid_tenant_id)
    assert repo.tenant_id == valid_tenant_id