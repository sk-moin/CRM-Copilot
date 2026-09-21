"""Background ingestion of an uploaded document.

Runs in the worker process, so it owns everything it needs: its own database
session, its own service graph. Nothing is carried over from the request that
enqueued it — only the document id and tenant, which arrive through Redis as
plain strings.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from uuid import UUID

from arq import Retry

from app.core import config
from app.core.database import AsyncSessionLocal
from app.rag.document_processing_service import DocumentProcessingService
from app.rag.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
)
from app.rag.embeddings.embedding_provider import create_embedding_provider
from app.rag.loaders.parser import create_document_parser
from app.rag.splitters.text_splitter import create_text_splitter
from app.rag.vectorstores.pgvector_store import PGVectorStore
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)

logger = logging.getLogger(__name__)


# Retrying a deterministic failure just burns the queue: an unreadable file
# is unreadable on the third attempt too, and a missing one is still missing.
# Everything the pipeline raises deliberately is in that category. Anything
# else -- a dropped connection, an embedding provider returning 503 -- is
# worth another go.
def _is_transient(exc: BaseException) -> bool:
    return not isinstance(exc, DocumentProcessingError)


def _backoff_seconds(attempt: int) -> int:
    """Wait longer each time, so a provider outage is not hammered.

    At the default three tries this waits 30s then 60s, about a minute and a
    half in total. It was 5s then 10s, which meant a twenty-second blip used
    up every attempt.
    """

    return min(600, 30 * (2 ** (attempt - 1)))


# The task enforces its own deadline, just inside arq's.
#
# arq applies `job_timeout` with `asyncio.wait_for`, which cancels the task.
# The task sees CancelledError -- a BaseException, so `except Exception`
# never catches it -- and arq's caller then sees TimeoutError, which is not
# in its retry set, so the job just ends. Left to arq alone a long-running
# job was neither recorded nor retried, and the document stayed at PARSING
# for good: F-58's defect one path over.
_MAX_TIMEOUT_MARGIN_SECONDS = 60


def _task_budget_seconds() -> int:
    """Always expire before arq does, so this module handles it.

    The margin scales with the budget rather than being a flat minute, so a
    short timeout stays usable: at the default 1800s the task gets 1740s,
    and a test can set a few seconds and still leave arq a slice.

    Caveat: this only fires at an await point. Parsing is synchronous, so a
    genuinely CPU-bound parse blocks the event loop and neither this nor
    arq's own `wait_for` can interrupt it. The awaits around embedding and
    the database are where a stuck job realistically sits.
    """

    # `JOB_TIMEOUT_SECONDS` is validated ge=2, and the worker uses the same
    # value, so this is always at least one second shorter than arq's.
    total = max(2, config.JOB_TIMEOUT_SECONDS)
    margin = min(_MAX_TIMEOUT_MARGIN_SECONDS, max(1, total // 4))

    return total - margin


@lru_cache(maxsize=1)
def _embedding_provider():
    """One provider per worker process, not one per job.

    The default provider loads a sentence-transformers model. Building it per
    job meant reloading it on every document and again on every retry. The
    worker is long-lived, so the natural scope is the process.

    Cached here rather than on `create_embedding_provider` itself: that
    factory is also a FastAPI dependency, and its own test patches
    `get_settings` and would stop seeing its patch through a cache.
    """

    return create_embedding_provider()


def _build_service(session, tenant_id: UUID) -> DocumentProcessingService:
    """Assemble the processing service against a worker-owned session.

    The API builds this through FastAPI dependencies, which do not exist here.
    Tenant scope comes from the argument, and every repository is constructed
    with it, so a task cannot reach another tenant's rows.
    """

    document_repository = KnowledgeDocumentRepository(
        session=session,
        tenant_id=tenant_id,
    )

    chunk_repository = DocumentChunkRepository(
        session=session,
        tenant_id=tenant_id,
    )

    return DocumentProcessingService(
        parser=create_document_parser(),
        splitter=create_text_splitter(),
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        vector_store=PGVectorStore(
            repository=chunk_repository,
            embedding_provider=_embedding_provider(),
        ),
    )


async def ingest_document(
    ctx: dict,
    document_id: str,
    tenant_id: str,
    *,
    delete_source: bool = True,
) -> dict:
    """Parse, chunk, embed and index a previously uploaded document.

    Retried by arq on failure. The status is only written as FAILED on the
    final attempt: recording it earlier would show a terminal state to anyone
    polling between retries, when the work is in fact still scheduled.

    `ctx` carries arq's `job_try`. It is a plain dict, so a test can call this
    directly without running a worker.
    """

    attempt = ctx.get("job_try", 1)

    # Read from config, not from `ctx`: arq only puts job_id, job_try,
    # enqueue_time and score in there. `WorkerSettings.max_tries` is this same
    # constant, so the two agree by construction. They would stop agreeing if
    # a per-function max_tries were ever set, which is why the test asserts
    # the retry behaviour rather than the equality.
    max_tries = config.JOB_MAX_TRIES
    is_last_attempt = attempt >= max_tries

    document_uuid = UUID(document_id)
    tenant_uuid = UUID(tenant_id)

    logger.info(
        "jobs.ingest_document.start",
        extra={
            "document_id": document_id,
            "attempt": attempt,
            "max_tries": max_tries,
        },
    )

    # The worker owns its session. `ctx` may carry a factory instead, which
    # is how a test drives the task without a running worker: the suite's
    # session lives in a transaction that is rolled back, so a task opening
    # its own connection would not see the fixture's data at all.
    session_factory = ctx.get("session_factory") or AsyncSessionLocal

    async with session_factory() as session:
        service = _build_service(session, tenant_uuid)

        try:
            # Nothing is written as FAILED here. Whether this failure is
            # terminal depends on the exception, which is not known yet.
            # The task owns its deadline, inside arq's, so expiry arrives
            # here as an ordinary exception instead of a cancellation this
            # handler cannot see.
            async with asyncio.timeout(_task_budget_seconds()):
                result = await service.process_document(
                    document_uuid,
                    record_failure=False,
                )

        except Exception as exc:
            transient = _is_transient(exc)
            retrying = transient and not is_last_attempt

            logger.exception(
                "jobs.ingest_document.failed",
                extra={
                    "document_id": document_id,
                    "attempt": attempt,
                    "transient": transient,
                    "terminal": not retrying,
                },
            )

            if retrying:
                # arq retries only when a task raises Retry; a plain
                # exception ends the job. Relying on max_tries alone meant
                # a failure was neither retried nor recorded, and the
                # document sat at PARSING for good with its file orphaned.
                raise Retry(defer=_backoff_seconds(attempt)) from exc

            # Terminal: record it before raising, or nobody polling ever
            # learns what happened. Except when there was no document to
            # begin with -- wrong tenant, or already deleted -- where there
            # is nothing to mark and the rollback would be pointless.
            if not isinstance(exc, DocumentNotFoundError):
                await service.record_failure(document_uuid, exc)

            # Whether to keep the upload depends on which kind of failure
            # this was, and the two are opposites.
            #
            # Deterministic: the file itself is the problem and no retry
            # will ever read it, so keeping it would let anyone park 25 MiB
            # per request in a shared directory by uploading rubbish with an
            # allowed extension. Delete it.
            #
            # Transient: a short outage used up the retries and the file is
            # the only copy, so deleting it would destroy a perfectly good
            # document. Keep it; the FAILED row holds its storage_path.
            if delete_source and not transient:
                await _remove_uploaded_file(session, tenant_uuid, document_uuid)

            raise

        if delete_source:
            await _remove_uploaded_file(session, tenant_uuid, document_uuid)

        logger.info(
            "jobs.ingest_document.ready",
            extra={
                "document_id": document_id,
                "chunk_count": result.chunk_count,
            },
        )

        return {
            "document_id": str(result.document_id),
            "chunk_count": result.chunk_count,
            "status": result.status.value,
        }


async def _remove_uploaded_file(session, tenant_id: UUID, document_id: UUID) -> None:
    """Delete the uploaded file once its contents are safely in the database.

    Best effort: a leftover file is untidy, but failing the job over it would
    turn a successful ingestion into a retry that re-embeds everything.
    """

    repository = KnowledgeDocumentRepository(session=session, tenant_id=tenant_id)

    document = await repository.get_by_id(document_id)

    if document is None or not document.storage_path:
        return

    _remove_source(document.storage_path)


def _remove_source(path: str | None) -> None:
    if not path:
        return

    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("jobs.ingest_document.cleanup_failed", exc_info=True)
