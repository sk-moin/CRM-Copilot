"""
tests/integration/conftest.py

Integration test fixtures for FastAPI API testing.

Provides:
- Shared PostgreSQL test database.
- Function-scoped AsyncSession with rollback isolation.
- FastAPI dependency overrides.
- Seeded tenant / organization / user hierarchy.
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio

from fastapi.testclient import TestClient

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.main import app
from app.core.database import get_db
from app.api.dependencies import get_current_user
from httpx import AsyncClient, ASGITransport
from packages.database.models.base import Base
from packages.database.models import (
    Tenant,
    Organization,
    User,
)

from packages.database.repositories.organization_repository import (
    OrganizationRepository,
)
from packages.database.repositories.user_repository import (
    UserRepository,
)
from packages.database.repositories.company_repository import (
    CompanyRepository,
)

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot"
)


@pytest_asyncio.fixture(scope="function")
async def _engine():
    """
    Shared PostgreSQL engine for integration tests.
    """

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )


    yield engine

    await engine.dispose()


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def _async_session(
    _engine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Fresh transaction per test.
    Rolls back after completion.
    """

    async with _engine.connect() as conn:
        transaction = await conn.begin()

        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


# --------------------------------------------------------------------------- #
# Client (unauthenticated)
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def client(_async_session):

    async def override_get_db():
        yield _async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Seed data
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def seeded_tenant(
    _async_session,
) -> Tenant:
    """
    Create test tenant.
    """

    tenant = Tenant(
        name="Test Tenant",
        subdomain="test-tenant",
    )

    _async_session.add(tenant)
    await _async_session.flush()

    return tenant


@pytest_asyncio.fixture(scope="function")
async def seeded_organization(
    seeded_tenant,
    _async_session,
) -> Organization:
    """
    Create organization.
    """

    repo = OrganizationRepository(
        session=_async_session,
        tenant_id=seeded_tenant.id,
    )

    organization = await repo.create(
        name="Test Organization",
        subdomain="test-org",
        tenant_id=seeded_tenant.id,
    )

    return organization


@pytest_asyncio.fixture(scope="function")
async def seeded_user(
    seeded_organization,
    _async_session,
) -> User:
    """
    Create authenticated user.
    """

    repo = UserRepository(
        session=_async_session,
        tenant_id=seeded_organization.tenant_id,
    )

    user = await repo.create(
        email="test-user@example.com",
        password_hash="integration-test-hash",
        role="OWNER",
        org_id=seeded_organization.id,
        tenant_id=seeded_organization.tenant_id,
    )

    return user


# --------------------------------------------------------------------------- #
# Authenticated client
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def authed_client(
    _async_session,
    seeded_user,
):

    async def override_get_db():
        yield _async_session

    async def override_get_current_user():
        return seeded_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()



@pytest_asyncio.fixture(scope="function")
async def seeded_company(
    seeded_organization,
    _async_session,
):
    repo = CompanyRepository(
        session=_async_session,
        tenant_id=seeded_organization.tenant_id,
    )

    company = await repo.create(
        name="Test Company",
        industry="Technology",
        org_id=seeded_organization.id,
        tenant_id=seeded_organization.tenant_id,
    )

    return company