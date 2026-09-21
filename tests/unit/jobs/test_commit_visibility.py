"""Progress is committed, not merely flushed.

This is the one claim the rest of the job tests cannot make. They inject the
suite's session, which is bound to a connection already inside a transaction
the fixture rolls back; SQLAlchemy joins that transaction, so `commit()` there
is indistinguishable from `flush()` and no assertion can tell them apart.

The whole point of the feature is that a second process can watch a job while
it runs. So this test uses real connections and real commits, on the
production path with no session injected, and cleans up after itself.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.jobs.tasks.ingest_document import ingest_document
from app.rag.vectorstores.pgvector_store import PGVectorStore
from packages.database.models import (
    KnowledgeDocument,
    Organization,
    Tenant,
    User,
)
from packages.database.models.document_chunk import DocumentChunk
from packages.database.models.enums import DocumentProcessingStatus


@pytest_asyncio.fixture
async def committed_upload(tmp_path, database_url):
    """A document that genuinely exists for every other connection."""

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # Its own engine, bound to this test's event loop. The application's
    # global engine is created at import time against whichever loop got
    # there first, which is what produced "Event loop is closed" here before.
    engine = create_async_engine(database_url, echo=False)
    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)

    # The task deliberately uses the application's global engine, which is
    # built at import time and pools connections belonging to whichever event
    # loop first touched it. pytest-asyncio gives each test a new loop, so
    # without this the second test in the file reaches for a socket whose
    # loop is gone: "'NoneType' object has no attribute 'send'".
    from app.core.database import engine as app_engine

    await app_engine.dispose()

    source = tmp_path / "notes.txt"
    source.write_text(
        "Acme Corp renewal is due in March. The contract covers 40 seats. " * 8,
        encoding="utf-8",
    )

    suffix = uuid.uuid4().hex[:8]

    async with sessionmaker() as session:
        tenant = Tenant(name=f"Commit {suffix}", subdomain=f"commit-{suffix}")
        session.add(tenant)
        await session.flush()

        org = Organization(
            tenant_id=tenant.id,
            name=f"Commit Org {suffix}",
            subdomain=f"commit-org-{suffix}",
            domain=f"commit-{suffix}.local",
        )
        session.add(org)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            org_id=org.id,
            email=f"commit-{suffix}@example.com",
            password_hash="x",
            role="OWNER",
        )
        session.add(user)
        await session.flush()

        document = KnowledgeDocument(
            tenant_id=tenant.id,
            org_id=org.id,
            owner_id=user.id,
            title="Commit visibility",
            filename="notes.txt",
            storage_path=str(source),
            document_type="txt",
            source_type="upload",
            mime_type="text/plain",
            file_size=source.stat().st_size,
            processing_status=DocumentProcessingStatus.UPLOADED,
        )
        session.add(document)

        # A real commit. Nothing above this line is visible to the worker.
        await session.commit()

        ids = (document.id, tenant.id, org.id, user.id)

    try:
        yield sessionmaker, ids, source
    finally:
        document_id, tenant_id, org_id, user_id = ids

        async with sessionmaker() as session:
            await session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document_id
                )
            )
            await session.execute(
                delete(KnowledgeDocument).where(
                    KnowledgeDocument.id == document_id
                )
            )
            await session.execute(delete(User).where(User.id == user_id))
            await session.execute(
                delete(Organization).where(Organization.id == org_id)
            )
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()

        await engine.dispose()


@pytest.mark.asyncio
async def test_parsing_is_visible_to_another_connection_mid_job(
    committed_upload,
):
    """Poll the status from a separate connection while the job is running.

    `index_chunks` is awaited between the PARSING commit and the READY commit,
    which makes it the honest place to look: if that first commit were only a
    flush, this read would still see UPLOADED.
    """

    sessionmaker, (document_id, tenant_id, _, _), _ = committed_upload

    seen: list[DocumentProcessingStatus] = []

    real_index = PGVectorStore.index_chunks

    async def peeking(self, chunks):
        async with sessionmaker() as observer:
            row = await observer.get(KnowledgeDocument, document_id)
            seen.append(row.processing_status)

        return await real_index(self, chunks)

    with patch.object(PGVectorStore, "index_chunks", peeking):
        # No session_factory in ctx: the task opens its own, as it does in the
        # worker. That is the path whose commits are under test.
        result = await ingest_document(
            {"job_try": 1},
            str(document_id),
            str(tenant_id),
            delete_source=False,
        )

    assert seen == [DocumentProcessingStatus.PARSING], (
        "another connection did not observe PARSING mid-job, so the status "
        "write was not committed"
    )

    assert result["status"] == DocumentProcessingStatus.READY.value

    async with sessionmaker() as observer:
        row = await observer.get(KnowledgeDocument, document_id)

        assert row.processing_status == DocumentProcessingStatus.READY
        assert row.chunk_count == result["chunk_count"]
        assert row.processed_at is not None


@pytest.mark.asyncio
async def test_a_failure_is_committed_where_another_connection_sees_it(
    committed_upload,
):
    """FAILED has to outlive the job, or nobody polling ever learns anything.

    This is the path that was genuinely broken: mark_failed ran on an aborted
    transaction and the status was discarded on rollback.
    """

    sessionmaker, (document_id, tenant_id, _, _), source = committed_upload

    source.unlink()

    with pytest.raises(Exception):
        await ingest_document(
            {"job_try": 3},
            str(document_id),
            str(tenant_id),
            delete_source=False,
        )

    async with sessionmaker() as observer:
        row = await observer.get(KnowledgeDocument, document_id)

        assert row.processing_status == DocumentProcessingStatus.FAILED
        assert row.error_message

        # The reason must name the cause without naming the server's disk.
        assert "notes.txt" in row.error_message
        assert str(source.parent) not in row.error_message


@pytest.mark.asyncio
async def test_an_unexpected_failure_does_not_reach_the_caller_verbatim(
    committed_upload,
):
    """Only messages written for a user survive to the status endpoint.

    `error_message` is returned verbatim by GET /documents/{id}/status. A
    driver or provider exception can carry a connection string, a query, or a
    filesystem path in its text, so anything outside the pipeline's own
    exception types has to collapse.
    """

    sessionmaker, (document_id, tenant_id, _, _), _ = committed_upload

    secret = "postgresql://postgres:postgres@10.0.0.7:5432/crm password=hunter2"

    async def exploding(self, chunks):
        raise RuntimeError(f"connection failed: {secret}")

    with patch.object(PGVectorStore, "index_chunks", exploding):
        with pytest.raises(RuntimeError):
            await ingest_document(
                {"job_try": 3},
                str(document_id),
                str(tenant_id),
                delete_source=False,
            )

    async with sessionmaker() as observer:
        row = await observer.get(KnowledgeDocument, document_id)
        status = row.processing_status
        message = row.error_message

    assert status == DocumentProcessingStatus.FAILED

    assert secret not in message
    assert "hunter2" not in message
    assert "RuntimeError" not in message

    # Still says something actionable rather than an empty FAILED.
    assert "internal error" in message.lower()
