"""Enqueue side of the background job queue.

The API process only ever enqueues; the worker process consumes. Both agree on
`JOB_QUEUE_NAME`, which is set explicitly rather than left at arq's default
because a Redis instance can be shared with something else — on at least one
dev machine it already is.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core import config

logger = logging.getLogger(__name__)

# arq discards a job the worker never picked up within `_expires` of being
# queued, defaulting to 24 hours: the document would stay UPLOADED for good
# with no failure recorded. A week gives an outage room to be noticed and
# the backlog to drain, without keeping jobs for ever.
JOB_EXPIRES_SECONDS = 7 * 24 * 60 * 60

_pool: Optional[ArqRedis] = None


def redis_settings() -> RedisSettings:
    """arq connection settings derived from the same REDIS_URL as the app."""

    return RedisSettings.from_dsn(config.REDIS_URL)


async def get_queue() -> ArqRedis:
    """Return the shared arq pool, creating it on first use.

    Cached like the application's other clients. The pool belongs to the event
    loop that created it, so tests must call `reset_queue` between loops.
    """

    global _pool

    if _pool is None:
        _pool = await create_pool(
            redis_settings(),
            default_queue_name=config.JOB_QUEUE_NAME,
        )

    return _pool


async def reset_queue() -> None:
    """Close the pool and drop it.

    Mirrors `app.core.redis_client.reset_redis`: the connection pool is bound
    to the loop that built it, and pytest-asyncio gives each test a new loop.
    """

    global _pool

    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            # Teardown must not mask the real failure.
            pass

        _pool = None


async def enqueue(task: str, *args: Any, **kwargs: Any) -> Optional[str]:
    """Enqueue a task and return its job id.

    `enqueue_job` is typed as returning an optional job, and returns None when
    a job with the same explicit id is already queued. No caller supplies
    `_job_id`, so arq generates a unique one and that branch is unreachable
    today. It is handled rather than asserted away because supplying an id is
    the obvious way to add deduplication later, and a silent None would then
    look like a successful enqueue.
    """

    queue = await get_queue()

    job = await queue.enqueue_job(
        task,
        *args,
        _queue_name=config.JOB_QUEUE_NAME,
        _expires=JOB_EXPIRES_SECONDS,
        **kwargs,
    )

    if job is None:
        logger.warning("jobs.enqueue.declined", extra={"task": task})
        return None

    return job.job_id
