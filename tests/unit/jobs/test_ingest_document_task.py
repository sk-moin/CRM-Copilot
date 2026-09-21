"""The ingestion task and the status lifecycle it drives.

The task is called directly with a plain dict for `ctx` rather than through a
running worker. An in-process worker in the suite would make every failure
ambiguous between the task and the harness.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from arq import Retry
from sqlalchemy import select

from app.core import config
from app.jobs.tasks import ingest_document as task_module
from app.jobs.tasks.ingest_document import ingest_document
from app.rag.exceptions import DocumentProcessingError
from packages.database.models import KnowledgeDocument
from packages.database.models.document_chunk import DocumentChunk
from packages.database.models.enums import DocumentProcessingStatus


@pytest_asyncio.fixture
async def uploaded(async_session, tenant, organization, user, tmp_path):
    """A committed document row plus its file, as upload leaves things."""

    source = tmp_path / "notes.txt"
    source.write_text(
        "Acme Corp renewal is due in March. "
        "The contract covers 40 seats. " * 5,
        encoding="utf-8",
    )

    document = KnowledgeDocument(
        tenant_id=tenant.id,
        org_id=organization.id,
        owner_id=user.id,
        title="Acme notes",
        filename="notes.txt",
        storage_path=str(source),
        document_type="txt",
        source_type="upload",
        mime_type="text/plain",
        file_size=source.stat().st_size,
        processing_status=DocumentProcessingStatus.UPLOADED,
    )

    async_session.add(document)
    await async_session.flush()

    return document, source


def _ctx(session, attempt: int = 1) -> dict:
    """arq's context, plus the suite's session.

    `job_try` is the only field the task reads, and it is one of the four keys
    arq actually puts in `ctx` (with job_id, enqueue_time and score). The
    retry limit comes from config, not from here.

    The task opens its own session in production. Here it must reuse the
    fixture's, because the fixture holds everything in a transaction that is
    rolled back at the end of the test: a second connection would see none of
    the setup data. What that cannot prove -- that the writes are committed --
    is covered separately in test_commit_visibility.py against real
    connections.
    """

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield session

    return {
        "job_try": attempt,
        "session_factory": _factory,
    }


def _raising_parser(exc: Exception):
    """A parser factory whose parser blows up with `exc`.

    Used for transient failures. The pipeline's own exception types are
    deliberately deterministic, so a generic error is what stands in for an
    unreachable provider or a dropped connection.
    """

    real_factory = task_module.create_document_parser

    def factory():
        # Captured before the patch goes on, or this calls itself.
        parser = real_factory()

        def failing(path):
            raise exc

        parser.parse = failing
        return parser

    return factory


async def _chunks_for(session, document_id):
    rows = await session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    return list(rows.scalars().all())


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_the_task_ingests_and_marks_ready(async_session, uploaded, tenant):
    document, source = uploaded

    result = await ingest_document(
        _ctx(async_session),
        str(document.id),
        str(tenant.id),
        delete_source=False,
    )

    assert result["status"] == DocumentProcessingStatus.READY.value
    assert result["chunk_count"] > 0

    await async_session.refresh(document)

    assert document.processing_status == DocumentProcessingStatus.READY
    assert document.processing_started_at is not None
    assert document.processed_at is not None
    assert document.chunk_count == result["chunk_count"]
    assert document.error_message is None


@pytest.mark.asyncio
async def test_running_twice_does_not_duplicate_chunks(
    async_session,
    uploaded,
    tenant,
):
    """arq retries, and a worker killed mid-embed will be retried."""

    document, _ = uploaded

    first = await ingest_document(
        _ctx(async_session), str(document.id), str(tenant.id), delete_source=False
    )
    second = await ingest_document(
        _ctx(async_session), str(document.id), str(tenant.id), delete_source=False
    )

    assert first["chunk_count"] == second["chunk_count"]

    chunks = await _chunks_for(async_session, document.id)

    assert len(chunks) == second["chunk_count"]

    indexes = sorted(c.chunk_index for c in chunks)
    assert indexes == list(range(len(chunks))), "no duplicate chunk indexes"


@pytest.mark.asyncio
async def test_the_source_file_is_removed_once_indexed(
    async_session,
    uploaded,
    tenant,
):
    document, source = uploaded

    assert source.exists()

    await ingest_document(_ctx(async_session), str(document.id), str(tenant.id))

    assert not source.exists()


# --------------------------------------------------------------------------- #
# Status is observable while the work runs
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_processing_is_recorded_before_the_slow_work_runs(
    async_session,
    uploaded,
    tenant,
):
    """Status must advance before parsing, not after the job finishes.

    This is the whole point of polling: a document that is being worked on has
    to look different from one that is merely queued. The parser is the first
    slow step, so the status is read at the moment it is called.
    """

    document, _ = uploaded
    seen: list = []

    real_factory = task_module.create_document_parser

    def _parser_that_records_status():
        parser = real_factory()
        original = parser.parse

        def recording(path):
            seen.append(document.processing_status)
            return original(path)

        parser.parse = recording
        return parser

    with patch.object(
        task_module,
        "create_document_parser",
        _parser_that_records_status,
    ):
        await ingest_document(
            _ctx(async_session),
            str(document.id),
            str(tenant.id),
            delete_source=False,
        )

    assert seen, "the parser was never called"
    assert seen[0] == DocumentProcessingStatus.PARSING

    await async_session.refresh(document)
    assert document.processing_status == DocumentProcessingStatus.READY


# --------------------------------------------------------------------------- #
# Failure and retry
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_missing_file_fails_terminally_on_the_first_attempt(
    async_session,
    uploaded,
    tenant,
):
    """Deterministic failures do not get retried.

    A file that is not there will not be there on the third attempt either.
    Retrying would only delay telling the user, and hold the queue while it
    did, so this is recorded immediately.
    """

    document, source = uploaded
    source.unlink()

    with pytest.raises(DocumentProcessingError):
        await ingest_document(
            _ctx(async_session, attempt=1),
            str(document.id),
            str(tenant.id),
            delete_source=False,
        )

    await async_session.refresh(document)

    assert document.processing_status == DocumentProcessingStatus.FAILED
    assert document.error_message

    assert await _chunks_for(async_session, document.id) == []


@pytest.mark.asyncio
async def test_a_transient_failure_asks_arq_to_retry_instead_of_failing(
    async_session,
    uploaded,
    tenant,
):
    """A retry is still coming, so nobody polling should see FAILED yet.

    It has to be raised as `Retry`: arq retries on that and on cancellation,
    and treats every other exception as the end of the job. Raising the
    original error here would have ended the job on attempt 1 while the code
    was still assuming two more were coming, so FAILED was never written.
    """

    document, _ = uploaded

    with patch.object(
        task_module,
        "create_document_parser",
        _raising_parser(RuntimeError("embedding host unreachable")),
    ):
        with pytest.raises(Retry):
            await ingest_document(
                _ctx(async_session, attempt=1),
                str(document.id),
                str(tenant.id),
                delete_source=False,
            )

    await async_session.refresh(document)

    assert document.processing_status != DocumentProcessingStatus.FAILED
    assert document.error_message is None


@pytest.mark.asyncio
async def test_a_retry_after_a_failure_can_still_succeed(
    async_session,
    uploaded,
    tenant,
):
    document, _ = uploaded

    with patch.object(
        task_module,
        "create_document_parser",
        _raising_parser(RuntimeError("embedding host unreachable")),
    ):
        with pytest.raises(Retry):
            await ingest_document(
                _ctx(async_session, attempt=1),
                str(document.id),
                str(tenant.id),
                delete_source=False,
            )

    result = await ingest_document(
        _ctx(async_session, attempt=2),
        str(document.id),
        str(tenant.id),
        delete_source=False,
    )

    assert result["status"] == DocumentProcessingStatus.READY.value

    await async_session.refresh(document)
    assert document.processing_status == DocumentProcessingStatus.READY
    assert document.error_message is None


@pytest.mark.asyncio
async def test_an_unknown_document_raises(async_session, tenant):
    with pytest.raises(Exception):
        await ingest_document(_ctx(async_session), str(uuid4()), str(tenant.id))


@pytest.mark.asyncio
async def test_the_retry_limit_comes_from_configuration(
    async_session,
    uploaded,
    tenant,
    monkeypatch,
):
    """Not a hardcoded 3.

    arq never puts `max_tries` in `ctx` -- it carries only job_id, job_try,
    enqueue_time and score -- so the task reads the same setting that
    `WorkerSettings.max_tries` is built from. Raising it here must make an
    attempt that would otherwise be terminal stop short of writing FAILED.
    """

    document, _ = uploaded

    flaky = _raising_parser(RuntimeError("embedding host unreachable"))

    # Attempt 3 of 5: still retryable.
    monkeypatch.setattr(config, "JOB_MAX_TRIES", 5)

    with patch.object(task_module, "create_document_parser", flaky):
        with pytest.raises(Retry):
            await ingest_document(
                _ctx(async_session, attempt=3),
                str(document.id),
                str(tenant.id),
                delete_source=False,
            )

    await async_session.refresh(document)

    assert document.processing_status != DocumentProcessingStatus.FAILED

    # Attempt 3 of 3: the same failure is now the last word.
    monkeypatch.setattr(config, "JOB_MAX_TRIES", 3)

    with patch.object(task_module, "create_document_parser", flaky):
        with pytest.raises(RuntimeError):
            await ingest_document(
                _ctx(async_session, attempt=3),
                str(document.id),
                str(tenant.id),
                delete_source=False,
            )

    await async_session.refresh(document)

    assert document.processing_status == DocumentProcessingStatus.FAILED
    assert document.error_message


@pytest.mark.asyncio
async def test_success_clears_a_reason_left_by_an_earlier_failure(
    async_session,
    uploaded,
    tenant,
):
    """A READY document must not still be showing why it once failed.

    `update_processing_result` skips None arguments, so it cannot clear a
    column; `mark_ready` has to do it explicitly. Without that a re-queued
    document reports READY with stale error text beside it.
    """

    document, _ = uploaded

    # Land it in FAILED the way a terminal failure does.
    with patch.object(
        task_module,
        "create_document_parser",
        _raising_parser(RuntimeError("embedding host unreachable")),
    ):
        with pytest.raises(RuntimeError):
            await ingest_document(
                _ctx(async_session, attempt=config.JOB_MAX_TRIES),
                str(document.id),
                str(tenant.id),
                delete_source=False,
            )

    await async_session.refresh(document)

    assert document.processing_status == DocumentProcessingStatus.FAILED
    assert document.error_message

    result = await ingest_document(
        _ctx(async_session, attempt=1),
        str(document.id),
        str(tenant.id),
        delete_source=False,
    )

    assert result["status"] == DocumentProcessingStatus.READY.value

    await async_session.refresh(document)

    assert document.processing_status == DocumentProcessingStatus.READY
    assert document.error_message is None, "the old reason survived a success"
