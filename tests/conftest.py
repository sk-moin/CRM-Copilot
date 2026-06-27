# tests/conftest.py

from sqlalchemy import select
import sys
from unittest import result
import uuid
from pathlib import Path
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add repo root BEFORE importing project modules
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from packages.database.models import (
    Tenant,
    Organization,
    User,
    AuditLog,
    AuditAction,
)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot"


@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        await conn.begin()

        session = AsyncSession(conn, expire_on_commit=False)

        yield session

        await conn.rollback()

    await engine.dispose()


# --------------------------------------------------------------------------- #
# Tenant
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def tenant(async_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        name="Test Tenant",
        subdomain=f"tenant-{uuid.uuid4().hex[:8]}",
    )

    async_session.add(tenant)
    await async_session.flush()

    return tenant


# --------------------------------------------------------------------------- #
# Organization
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def organization(
    async_session: AsyncSession,
    tenant: Tenant,
) -> Organization:
    organization = Organization(
        tenant_id=tenant.id,
        name="Test Organization",
        subdomain=f"org-{uuid.uuid4().hex[:8]}",
        domain="example.com",
    )

    async_session.add(organization)
    await async_session.flush()

    return organization


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="function")
async def user(
    async_session: AsyncSession,
    tenant: Tenant,
    organization: Organization,
) -> User:
    user = User(
        tenant_id=tenant.id,
        org_id=organization.id,
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed-password",
        role="ADMIN",
    )

    async_session.add(user)
    await async_session.flush()

    return user


# --------------------------------------------------------------------------- #
# Audit Log
# --------------------------------------------------------------------------- #
