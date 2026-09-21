"""A background job must not become a way around tenant scope.

The task arguments arrive through Redis as plain strings. Anything that can
write to that queue can therefore name any document id it likes. The tenant
id is the only scope the task has, so the pairing has to be enforced rather
than trusted: a job naming tenant B and a document owned by tenant A must do
nothing at all, not process it under B.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select

from app.jobs.tasks.ingest_document import ingest_document
from packages.database.models import KnowledgeDocument, Organization, Tenant, User
from packages.database.models.document_chunk import DocumentChunk
from packages.database.models.enums import DocumentProcessingStatus


def _ctx(session) -> dict:
    @asynccontextmanager
    async def _factory():
        yield session

    return {"job_try": 1, "max_tries": 3, "session_factory": _factory}


async def _seed(session, label: str):
    tenant = Tenant(name=f"Tenant {label}", subdomain=f"jobs-{label}")
    session.add(tenant)
    await session.flush()

    org = Organization(
        tenant_id=tenant.id,
        name=f"Org {label}",
        subdomain=f"jobs-org-{label}",
        domain=f"jobs-org-{label}.local",
    )
    session.add(org)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        org_id=org.id,
        email=f"jobs-{label}@example.com",
        password_hash=f"hash-{label}",
        role="OWNER",
    )
    session.add(user)
    await session.flush()

    return tenant, org, user


@pytest.mark.asyncio
async def test_a_job_cannot_ingest_another_tenants_document(
    async_session,
    tmp_path,
):
    tenant_a, org_a, user_a = await _seed(async_session, "a")
    tenant_b, _, _ = await _seed(async_session, "b")

    source = tmp_path / "secret.txt"
    source.write_text(
        "Tenant A's renewal terms and pricing. " * 10,
        encoding="utf-8",
    )

    document = KnowledgeDocument(
        tenant_id=tenant_a.id,
        org_id=org_a.id,
        owner_id=user_a.id,
        title="A's notes",
        filename="secret.txt",
        storage_path=str(source),
        document_type="txt",
        source_type="upload",
        mime_type="text/plain",
        file_size=source.stat().st_size,
        processing_status=DocumentProcessingStatus.UPLOADED,
    )

    async_session.add(document)
    await async_session.flush()

    # The job names tenant B. The document belongs to tenant A.
    with pytest.raises(Exception):
        await ingest_document(
            _ctx(async_session),
            str(document.id),
            str(tenant_b.id),
            delete_source=False,
        )

    await async_session.refresh(document)

    # Untouched: not processed, not marked failed under the wrong tenant, and
    # above all not chunked and embedded into B's searchable index.
    assert document.processing_status == DocumentProcessingStatus.UPLOADED
    assert document.chunk_count in (0, None)

    rows = await async_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )

    assert list(rows.scalars().all()) == []

    # The source file survives: it is still A's pending upload.
    assert source.exists()
