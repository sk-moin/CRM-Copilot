# tests/conftest.py

import sys
import uuid
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


# Add repo root BEFORE importing project modules
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Force the deterministic in-process LLM before any project module reads
# settings. Integration tests should not depend on a live third-party API:
# it costs money, needs network, and makes a red suite ambiguous between
# "our code broke" and "the provider is having a bad day".
import os  # noqa: E402

os.environ["LLM_PROVIDER"] = "mock"

# Same reasoning, and the one that was actually missing: EMBEDDING_PROVIDER
# defaults to "huggingface", which downloads and loads sentence-transformers
# on first use. Every run so far has been passing it on the command line, so
# the documented Verify command did not work as documented.
os.environ["EMBEDDING_PROVIDER"] = "mock"

# Settings are a module-level singleton built at import time, so the line above
# only wins if nothing imported app.core.config before this conftest. A plugin
# loaded with -p, pytest-env, or a repo-root conftest would load first and
# silently re-point the suite at the live paid provider. Fail loudly instead.
from app.core.config import get_settings  # noqa: E402

# Bound to locals before asserting, deliberately. pytest rewrites assertions
# by rendering each operand, so `assert get_settings().X == "mock"` puts the
# whole Settings repr in the failure message -- and JWT_SECRET, GROQ_API_KEY,
# OPENAI_API_KEY, OPENROUTER_API_KEY, HF_TOKEN and LANGSMITH_API_KEY are plain
# str, not SecretStr, so every one of them would be printed verbatim into a
# terminal scrollback, a pasted traceback or a public CI log. Comparing two
# locals keeps the message to the two strings that matter.
_settings = get_settings()
_llm_provider = _settings.LLM_PROVIDER
_embedding_provider = _settings.EMBEDDING_PROVIDER

assert _llm_provider == "mock", (
    "tests/conftest.py ran after app.core.config was already imported, so the "
    "LLM_PROVIDER pin did not take effect and the suite would hit the live "
    "provider. Move the pin into pytest.ini if a plugin now loads first."
)

assert _embedding_provider == "mock", (
    "EMBEDDING_PROVIDER is not mock, so the suite would load "
    "sentence-transformers. Set EMBEDDING_PROVIDER=mock, or move the pin "
    "into pytest.ini if a plugin now loads before this conftest."
)


from packages.database.models import (
    Tenant,
    Organization,
    User,
)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot"


@pytest.fixture(scope="session")
def database_url() -> str:
    """The one place the suite's DSN is written down.

    Tests that need their own engine -- because they must see genuinely
    committed rows -- take this rather than repeating the literal.
    """

    return DATABASE_URL


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
        org_id=organization.id,
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

@pytest_asyncio.fixture(autouse=True)
async def _reset_redis_between_tests():
    """Drop the cached Redis client after each test.

    `get_redis()` caches a client whose connection pool belongs to the event
    loop that built it. pytest-asyncio gives each test its own loop, so without
    this the second test inherits a pool tied to a closed loop.
    """

    yield

    from app.core.redis_client import reset_redis

    await reset_redis()
