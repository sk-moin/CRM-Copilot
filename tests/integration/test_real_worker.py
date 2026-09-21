"""The task driven by a real arq worker, not called directly.

Every other job test calls `ingest_document` with a hand-built `ctx`, so
arq's own control flow never participates. Three defects hid in exactly that
gap, and each needed a real worker to see:

* a plain exception ends a job instead of retrying it, so the code's
  "a retry is coming, don't record FAILED yet" left documents at PARSING;
* `job_timeout` cancels the task with `CancelledError`, which `except
  Exception` cannot catch, and arq then treats the resulting `TimeoutError`
  as terminal -- stranding the document the same way;
* a job the worker never starts is dropped once `_expires` passes.

So this file runs the real thing: a real Redis, a real worker, real commits.
It is slower than the rest of the suite, and that is the point.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.jobs.tasks.ingest_document as task_module
from app.core import config
from app.jobs.tasks.ingest_document import ingest_document
from packages.database.models import (
    KnowledgeDocument,
    Organization,
    Tenant,
    User,
)
from app.rag.exceptions import UnsupportedDocumentTypeError
from packages.database.models.document_chunk import DocumentChunk
from packages.database.models.enums import DocumentProcessingStatus

# Compose publishes the project's Redis on 6380, because another Redis
# already owns 6379 on at least one dev machine.
REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380")

# A queue of its own, so a developer's worker cannot eat these jobs and
# these jobs cannot reach a developer's worker.
QUEUE = "crm_copilot:test-jobs"


pytestmark = pytest.mark.asyncio


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(REDIS_URL)


_REDIS_REACHABLE: bool | None = None


async def _redis_available() -> bool:
    """Probed once per session, not once per test.

    Connecting to a Redis that is not there costs about twelve seconds, and
    the fixture is function-scoped, so a developer without compose running
    used to pay that for every test in this file just to reach the skip.
    """

    global _REDIS_REACHABLE

    if _REDIS_REACHABLE is None:
        try:
            pool = await create_pool(_redis_settings())
        except Exception:
            _REDIS_REACHABLE = False
        else:
            await pool.aclose()
            _REDIS_REACHABLE = True

    return _REDIS_REACHABLE


@pytest_asyncio.fixture
async def worker_env(tmp_path, database_url):
    """A committed document, a clean queue, and an engine to observe with."""

    if not await _redis_available():
        # Skipping locally is a convenience. Skipping in CI would silently
        # remove the only coverage of arq's real control flow, which is
        # where three separate stranding defects hid, so fail there.
        if os.environ.get("CI"):
            raise RuntimeError(
                f"no Redis at {REDIS_URL}; set TEST_REDIS_URL. These tests "
                "are the only coverage of the worker's retry, timeout and "
                "failure-recording behaviour and must not be skipped in CI."
            )

        pytest.skip(f"no Redis at {REDIS_URL}")

    from app.core.database import engine as app_engine

    # The task uses the application's global engine, whose pooled
    # connections belong to whichever event loop first touched it.
    await app_engine.dispose()

    engine = create_async_engine(database_url, echo=False)
    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)

    tag = uuid.uuid4().hex[:8]

    source = tmp_path / f"worker-{tag}.txt"
    source.write_text(
        "Acme Corp renewal is due in March. 40 seats. " * 12,
        encoding="utf-8",
    )

    async with sessionmaker() as session:
        tenant = Tenant(name=f"Worker {tag}", subdomain=f"worker-{tag}")
        session.add(tenant)
        await session.flush()

        org = Organization(
            tenant_id=tenant.id,
            name=f"Worker Org {tag}",
            subdomain=f"worker-org-{tag}",
            domain=f"worker-{tag}.local",
        )
        session.add(org)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            org_id=org.id,
            email=f"worker-{tag}@example.com",
            password_hash="x",
            role="OWNER",
        )
        session.add(user)
        await session.flush()

        document = KnowledgeDocument(
            tenant_id=tenant.id,
            org_id=org.id,
            owner_id=user.id,
            title=f"Worker {tag}",
            filename=source.name,
            storage_path=str(source),
            document_type="txt",
            source_type="upload",
            mime_type="text/plain",
            file_size=source.stat().st_size,
            processing_status=DocumentProcessingStatus.UPLOADED,
        )
        session.add(document)
        await session.commit()

        ids = (document.id, tenant.id, org.id, user.id)

    pool = await create_pool(_redis_settings(), default_queue_name=QUEUE)

    try:
        yield sessionmaker, pool, ids, source
    finally:
        # The engines are released in their own finally: the deletes below
        # touch real committed rows, and a failure in one of them must not
        # leak a connection pool for the rest of the session.
        try:
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

            # Leave nothing queued for the next run, and no stale health key.
            await pool.delete(QUEUE)
            await pool.delete(f"{QUEUE}:health-check")
        finally:
            await pool.aclose()
            await engine.dispose()


async def _drain(pool, *, seconds=45.0, max_jobs=8):
    """Run a real worker in burst mode until the queue empties."""

    worker = Worker(
        functions=[ingest_document],
        redis_pool=pool,
        queue_name=QUEUE,
        max_tries=config.JOB_MAX_TRIES,
        job_timeout=config.JOB_TIMEOUT_SECONDS,
        burst=True,
        max_burst_jobs=max_jobs,
        poll_delay=0.1,
        retry_jobs=True,
        handle_signals=False,
    )

    # `worker.close()` is deliberately not called: it sends SIGUSR1, which
    # does not exist on Windows, and it would also close the pool the
    # fixture owns and reuses. In burst mode `async_run` returns once the
    # queue is empty, and the fixture does the cleanup.
    try:
        await asyncio.wait_for(worker.async_run(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


async def _status(sessionmaker, document_id):
    async with sessionmaker() as session:
        row = await session.get(KnowledgeDocument, document_id)
        await session.refresh(row)
        return row.processing_status, row.error_message, row.chunk_count


async def test_a_real_worker_ingests_the_document(worker_env):
    sessionmaker, pool, (document_id, tenant_id, _, _), source = worker_env

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool)

    status, message, chunks = await _status(sessionmaker, document_id)

    assert status == DocumentProcessingStatus.READY
    assert chunks > 0
    assert message is None
    assert not source.exists(), "the upload is removed once it is indexed"


async def test_a_job_that_outruns_its_budget_still_ends_in_failed(
    worker_env,
    monkeypatch,
):
    """The defect this file exists for, exercised as a real timeout.

    arq enforces `job_timeout` by cancelling the task. Cancellation reaches
    the task as CancelledError, a BaseException that `except Exception`
    cannot catch, and arq then sees TimeoutError, which is not in its retry
    set -- so the job simply ends. Unless the task owns a deadline inside
    arq's, the document is left at PARSING with no error and no retry.

    Nothing here raises TimeoutError by hand: `index_chunks` is made slower
    than the budget and the deadline is left to fire on its own. Remove the
    `asyncio.timeout` from the task and this test goes back to PARSING.
    """

    sessionmaker, pool, (document_id, tenant_id, _, _), _ = worker_env

    from app.rag.vectorstores.pgvector_store import PGVectorStore

    # Budget 6s for the task, 8s for arq: long enough to reach indexing,
    # far shorter than the sleep below.
    monkeypatch.setattr(config, "JOB_TIMEOUT_SECONDS", 8)
    monkeypatch.setattr(config, "JOB_MAX_TRIES", 1)

    async def crawling(self, chunks):
        await asyncio.sleep(60)

    monkeypatch.setattr(PGVectorStore, "index_chunks", crawling)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool, seconds=40.0)

    status, message, _ = await _status(sessionmaker, document_id)

    assert status == DocumentProcessingStatus.FAILED, (
        "a job that ran out of time was left at "
        f"{status.value} with nothing recorded"
    )
    assert message
    assert "internal error" in message.lower()

    # The spec's done-when is "FAILED with a message and no chunks". The
    # deadline expires by cancelling, which skips the rollback inside
    # process_document, so without a rollback before recording the failure
    # the half-finished ingestion is committed alongside it: chunks with no
    # embedding, which retrieval filters on neither.
    async with sessionmaker() as session:
        rows = await session.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )
        chunks = list(rows.scalars().all())

    assert chunks == [], (
        f"a timed-out job left {len(chunks)} chunk(s) behind"
    )


async def test_a_job_stalled_inside_a_database_call_still_ends_in_failed(
    worker_env,
    monkeypatch,
):
    """The other shape of the same defect.

    When the deadline expires during a database await, the cancellation
    leaves the session needing a rollback. Recording the failure on it then
    raised PendingRollbackError, nothing was written, and the document was
    left at PARSING -- the original defect, in the path the timeout is
    actually about.
    """

    from sqlalchemy import text

    from app.rag.vectorstores.pgvector_store import PGVectorStore

    sessionmaker, pool, (document_id, tenant_id, _, _), _ = worker_env

    monkeypatch.setattr(config, "JOB_TIMEOUT_SECONDS", 8)
    monkeypatch.setattr(config, "JOB_MAX_TRIES", 1)

    async def stalling(self, chunks):
        # Blocks on the task's own session, so the cancellation lands
        # mid-statement rather than on a plain sleep.
        await self.repository.session.execute(text("SELECT pg_sleep(60)"))

    monkeypatch.setattr(PGVectorStore, "index_chunks", stalling)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool, seconds=40.0)

    status, message, _ = await _status(sessionmaker, document_id)

    assert status == DocumentProcessingStatus.FAILED, (
        f"stalled in the database and was left at {status.value}"
    )
    assert message


async def test_a_deterministic_failure_removes_the_unusable_upload(
    worker_env,
    monkeypatch,
):
    """The file is the problem, so no retry will ever read it.

    Keeping it would let any authenticated caller park the maximum upload
    size in the shared directory on every request, by sending rubbish with
    an allowed extension.
    """

    sessionmaker, pool, (document_id, tenant_id, _, _), source = worker_env

    real_factory = task_module.create_document_parser

    def unreadable_factory():
        parser = real_factory()

        def unreadable(path):
            raise UnsupportedDocumentTypeError("Unsupported document type")

        parser.parse = unreadable
        return parser

    monkeypatch.setattr(task_module, "create_document_parser", unreadable_factory)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool)

    status, _, _ = await _status(sessionmaker, document_id)

    assert status == DocumentProcessingStatus.FAILED
    assert not source.exists(), "an unusable upload was left on disk"


async def test_a_transient_failure_is_retried_then_recorded(
    worker_env,
    monkeypatch,
):
    """arq only reschedules on Retry, and the last attempt must record."""

    sessionmaker, pool, (document_id, tenant_id, _, _), _ = worker_env

    attempts: list[int] = []
    real_factory = task_module.create_document_parser

    def flaky_factory():
        parser = real_factory()

        def unreachable(path):
            attempts.append(1)
            raise RuntimeError("embedding host unreachable")

        parser.parse = unreachable
        return parser

    monkeypatch.setattr(task_module, "create_document_parser", flaky_factory)
    # The real schedule's shape, compressed so the test is not 90 seconds.
    monkeypatch.setattr(task_module, "_backoff_seconds", lambda attempt: 1)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool, seconds=60.0)

    status, message, _ = await _status(sessionmaker, document_id)

    assert len(attempts) == config.JOB_MAX_TRIES, (
        f"expected {config.JOB_MAX_TRIES} attempts, saw {len(attempts)}"
    )
    assert status == DocumentProcessingStatus.FAILED
    assert message
    assert "unreachable" not in message


async def test_a_deterministic_failure_is_not_retried(worker_env, monkeypatch):
    """An unreadable file will not read on the third attempt either."""

    sessionmaker, pool, (document_id, tenant_id, _, _), source = worker_env

    source.unlink()

    attempts: list[int] = []
    real_factory = task_module.create_document_parser

    def counting_factory():
        attempts.append(1)
        return real_factory()

    monkeypatch.setattr(task_module, "create_document_parser", counting_factory)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool)

    status, message, _ = await _status(sessionmaker, document_id)

    assert len(attempts) == 1, f"a deterministic failure ran {attempts} times"
    assert status == DocumentProcessingStatus.FAILED
    assert message

    # Named for the person who uploaded it: the parser only ever saw the
    # generated storage path, so the name has to come off the document row.
    assert message.startswith(f"{source.name}: ")
    assert str(source.parent) not in message


async def test_the_upload_survives_a_terminal_failure(worker_env, monkeypatch):
    """The file is the only copy, so a failure must not destroy it.

    A short outage can use up every retry in about a minute and a half. If
    the last attempt deleted the upload, that outage would cost the document
    permanently; keeping it means a FAILED row can be re-queued.
    """

    sessionmaker, pool, (document_id, tenant_id, _, _), source = worker_env

    real_factory = task_module.create_document_parser

    def flaky_factory():
        parser = real_factory()

        def unreachable(path):
            raise RuntimeError("embedding host unreachable")

        parser.parse = unreachable
        return parser

    monkeypatch.setattr(task_module, "create_document_parser", flaky_factory)
    monkeypatch.setattr(config, "JOB_MAX_TRIES", 1)

    await pool.enqueue_job(
        "ingest_document",
        str(document_id),
        str(tenant_id),
        _queue_name=QUEUE,
    )

    await _drain(pool)

    status, _, _ = await _status(sessionmaker, document_id)

    assert status == DocumentProcessingStatus.FAILED
    assert source.exists(), "a terminal failure destroyed the only copy"
