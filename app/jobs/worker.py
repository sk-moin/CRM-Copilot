"""arq worker entry point.

Run it with:

    arq app.jobs.worker.WorkerSettings

The worker is a separate process from the API. Nothing from a request may
reach a task: arguments are serialised through Redis, so they must be
JSON-friendly, and a task opens its own database session.
"""

from __future__ import annotations

import logging

from app.core import config
from app.jobs.queue import redis_settings
from app.jobs.tasks.ingest_document import ingest_document

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "worker.startup",
        extra={"queue": config.JOB_QUEUE_NAME},
    )


async def shutdown(ctx: dict) -> None:
    """Release anything the tasks left open.

    A task may have built the Redis client or the LLM provider singleton; both
    hold connection pools bound to this loop.
    """

    from app.core.redis_client import reset_redis

    await reset_redis()

    logger.info("worker.shutdown")


class WorkerSettings:
    """arq configuration.

    `max_tries` is shared with the task, which uses it to decide whether a
    failure is the final one and should be recorded as terminal rather than
    retried.
    """

    functions = [ingest_document]

    redis_settings = redis_settings()

    queue_name = config.JOB_QUEUE_NAME

    max_tries = config.JOB_MAX_TRIES

    # Embedding a large document on CPU is slow, and the default 300s would
    # kill a legitimate job midway. arq does NOT retry a timeout, so this is
    # a backstop only: the task sets its own, shorter deadline and handles
    # expiry itself. Both come from one setting so they cannot drift.
    job_timeout = config.JOB_TIMEOUT_SECONDS

    on_startup = startup
    on_shutdown = shutdown
