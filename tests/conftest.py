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


from packages.database.models import (
    KnowledgeDocument,
    DocumentChunk,
    Conversation,
)

from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)


@pytest_asyncio.fixture
async def retrieval_trace(
    async_session,
    tenant,
):
    repo = RetrievalTraceRepository(
        async_session,
        tenant.id,
    )

    trace = await repo.create(
        conversation_id=None,
        query="Repository test",
    )

    return trace


@pytest_asyncio.fixture
async def knowledge_document(
    async_session,
    tenant,
    organization,
):
    document = KnowledgeDocument(
        tenant_id=tenant.id,
        organization_id=organization.id,
        owner_id=None,
        title="Repository Document",
        filename="document.pdf",
        storage_path="/tmp/document.pdf",
        document_type="pdf",
        source_type="upload",
        mime_type="application/pdf",
        file_size=100,
    )

    async_session.add(document)
    await async_session.flush()

    return document


@pytest_asyncio.fixture
async def document_chunk(
    async_session,
    tenant,
    knowledge_document,
):
    chunk = DocumentChunk(
        tenant_id=tenant.id,
        document_id=knowledge_document.id,
        chunk_index=0,
        content="Repository chunk",
        token_count=8,
        start_char=0,
        end_char=16,
    )

    async_session.add(chunk)
    await async_session.flush()

    return chunk

@pytest_asyncio.fixture
async def conversation(
    async_session,
    tenant,
    organization,
    user,
):
    conversation = Conversation(
        tenant_id=tenant.id,
        org_id=organization.id,
        user_id=user.id,
        title="Test Conversation",
    )

    async_session.add(conversation)
    await async_session.flush()

    return conversation