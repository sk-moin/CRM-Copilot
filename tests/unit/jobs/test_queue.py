"""The enqueue side of the queue.

The queue name is the whole subject here. The dev Redis on this project is
shared with an unrelated container, so relying on arq's default queue would
let a stray worker consume this project's jobs, or this worker consume theirs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import config
from app.jobs import queue as queue_module


@pytest.mark.asyncio
async def test_enqueue_targets_the_configured_queue():
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job-1"))

    with patch.object(queue_module, "get_queue", AsyncMock(return_value=pool)):
        job_id = await queue_module.enqueue("ingest_document", "doc-1", "tenant-1")

    assert job_id == "job-1"

    pool.enqueue_job.assert_awaited_once()

    args = pool.enqueue_job.await_args

    assert args.args == ("ingest_document", "doc-1", "tenant-1")
    assert args.kwargs["_queue_name"] == config.JOB_QUEUE_NAME


@pytest.mark.asyncio
async def test_enqueue_maps_a_declined_job_to_none():
    """Our wrapper's handling of arq's Optional return, not arq's own.

    No caller passes `_job_id`, so arq always generates a unique one and
    never actually declines. This pins that if it ever did -- which is what
    adding deduplication would mean -- the caller gets None rather than an
    exception or a bogus id.
    """

    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=None)

    with patch.object(queue_module, "get_queue", AsyncMock(return_value=pool)):
        assert await queue_module.enqueue("ingest_document", "doc-1") is None


def test_the_worker_consumes_the_queue_the_api_writes_to():
    """The two halves agree, or jobs are enqueued into a void.

    This is cheap to get wrong and expensive to notice: nothing errors, the
    upload returns 202, and the document simply stays UPLOADED forever.
    """

    from app.jobs.worker import WorkerSettings

    assert WorkerSettings.queue_name == config.JOB_QUEUE_NAME

    registered = {fn.__name__ for fn in WorkerSettings.functions}

    assert "ingest_document" in registered
