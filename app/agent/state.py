"""
LangGraph Agent State.

Shared state passed between graph nodes.
"""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID

from langchain_core.documents import Document


class AgentState(TypedDict):
    """
    Shared LangGraph state.
    """

    conversation_id: UUID
    tenant_id: UUID
    org_id: UUID
    user_id: UUID

    query: str

    messages: list[Any]

    retrieved_documents: list[Document]
    retrieval_metadata: dict[str, Any]

    prompt: str

    response: str | None

    citations: list[dict[str, Any]]

    usage: dict[str, Any]

    errors: list[dict[str, Any]]

    finish_reason: str