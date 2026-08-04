"""
Tracing helpers.

Reusable helpers for instrumenting CRM Copilot with LangSmith.

Responsibilities
----------------
- Trace LangGraph execution
- Trace retrieval operations
- Trace LLM invocations
- Trace tool execution
- Attach CRM metadata to traces

Notes
-----
These helpers intentionally remain framework-agnostic. Business logic
should call these utilities rather than interacting with LangSmith
directly.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Iterator

from langsmith import traceable
from langsmith import tracing_context as ls_tracing_context

def traced(
    *,
    name: str,
    run_type: str,
    tags: list[str] | None = None,
) -> Callable[..., Any]:
    """
    Decorator for tracing a function with LangSmith.
    """
    return traceable(
        name=name,
        run_type=run_type,
        tags=tags or [],
    )


@contextmanager
def trace_context(
    *,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
):
    with ls_tracing_context(
        enabled=True,
        metadata=metadata or {},
        tags=tags or [],
    ):
        yield


def build_trace_metadata(
    *,
    tenant_id: Any,
    org_id: Any,
    conversation_id: Any | None = None,
    user_id: Any | None = None,
    embedding_model=None,
    llm_model=None,
    vector_store=None,
    retrieved_chunks=None,
    top_k=None,
) -> dict[str, str]:
    """
    Build standard CRM metadata for LangSmith traces.
    """
    metadata: dict[str, str] = {
        "tenant_id": str(tenant_id),
        "org_id": str(org_id),
    }

    if conversation_id is not None:
        metadata["conversation_id"] = str(conversation_id)

    if user_id is not None:
        metadata["user_id"] = str(user_id)

    return metadata


__all__ = [
    "build_trace_metadata",
    "trace_context",
    "traced",
]