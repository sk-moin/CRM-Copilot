"""Ambient correlation id for audit entries.

An approved agent action writes two kinds of audit row: the ones
`AgentActionService` writes about the action itself, and the one the CRM
service writes about the row it changed. Only the first carried a
`correlation_id`, so the audit log alone could not answer "the agent proposed
X, what changed?" without going out to `agent_action.result_entity_id` and back.

The CRM services build their own `AuditService` internally, so passing an id
down would mean adding a parameter to five service constructors for a single
caller. A context variable reaches the same depth without changing any
signature, and is scoped to the `with` block rather than the process.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

_correlation_id: ContextVar[Optional[uuid.UUID]] = ContextVar(
    "audit_correlation_id",
    default=None,
)


def current_correlation_id() -> Optional[uuid.UUID]:
    """The correlation id in scope, or None outside a correlated block."""

    return _correlation_id.get()


@contextmanager
def correlated_audit(correlation_id: uuid.UUID) -> Iterator[None]:
    """Tag every audit entry written inside this block.

    An explicit `correlation_id` passed to `log_event` still wins; this only
    supplies a default. The token is reset on exit, including on an exception,
    so a failure cannot leak the id into unrelated work on the same task.
    """

    token = _correlation_id.set(correlation_id)

    try:
        yield
    finally:
        _correlation_id.reset(token)
