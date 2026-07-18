"""
app/agent/state.py

LangGraph state definition for the CRM Copilot AI Agent.

The AgentState object is passed between every LangGraph node and
contains all information required during a single agent execution.

The state begins with the incoming user request and is gradually
enriched by each node:

START
    ↓
Retrieve Node
    ↓
Prompt Node
    ↓
Generate Node
    ↓
Finish Node
"""

from __future__ import annotations

from typing import Any
from typing import NotRequired
from typing import TypedDict
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage


# --------------------------------------------------------------------------- #
# Helper Types
# --------------------------------------------------------------------------- #


class TokenUsage(TypedDict):
    """
    Token usage returned by the LLM provider.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Citation(TypedDict):
    """
    Citation generated from a retrieved document.
    """

    document_id: str
    chunk_id: str
    title: str


class AgentError(TypedDict):
    """
    Error recorded during graph execution.
    """

    node: str
    message: str


# --------------------------------------------------------------------------- #
# Agent State
# --------------------------------------------------------------------------- #


class AgentState(TypedDict):
    """
    Shared LangGraph state.

    Required fields are supplied when execution begins.

    Optional fields are populated progressively as each node
    completes its work.
    """

    # ------------------------------------------------------------------ #
    # Request Context
    # ------------------------------------------------------------------ #

    conversation_id: UUID
    tenant_id: UUID
    user_id: UUID | None

    query: str

    messages: list[BaseMessage]

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    retrieved_documents: NotRequired[list[Document]]

    retrieval_metadata: NotRequired[dict[str, Any]]

    retrieval_trace_id: NotRequired[UUID]

    # ------------------------------------------------------------------ #
    # Prompt
    # ------------------------------------------------------------------ #

    prompt: NotRequired[str]

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #

    response: NotRequired[str]

    usage: NotRequired[TokenUsage]

    model: NotRequired[str]

    finish_reason: NotRequired[str]

    # ------------------------------------------------------------------ #
    # Streaming
    # ------------------------------------------------------------------ #

    stream: NotRequired[bool]

    # ------------------------------------------------------------------ #
    # Output
    # ------------------------------------------------------------------ #

    citations: NotRequired[list[Citation]]

    # ------------------------------------------------------------------ #
    # Errors
    # ------------------------------------------------------------------ #

    errors: NotRequired[list[AgentError]]