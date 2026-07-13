"""
Pydantic schemas for Retrieval-Augmented Generation.

These schemas define the request and response contracts for
question answering over the knowledge base.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


class RAGQueryRequest(BaseModel):
    """Request to execute a RAG query."""

    query: str = Field(
        min_length=1,
        max_length=4000,
        description="Natural language question.",
    )

    conversation_id: UUID | None = Field(
        default=None,
        description="Conversation associated with the query.",
    )

    document_id: UUID | None = Field(
        default=None,
        description="Restrict retrieval to a single document.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of chunks to retrieve.",
    )

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score.",
    )


# --------------------------------------------------------------------------- #
# Source
# --------------------------------------------------------------------------- #


class RAGSource(BaseModel):
    """Retrieved source document."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID

    document_id: UUID

    chunk_index: int

    title: str | None = None

    filename: str | None = None

    content: str

    similarity_score: float

    metadata: dict = Field(
        default_factory=dict,
    )


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #


class RAGQueryResponse(BaseModel):
    """Response returned by the RAG pipeline."""

    answer: str

    retrieved_chunks: int

    sources: list[RAGSource]


# --------------------------------------------------------------------------- #
# Retrieval Only
# --------------------------------------------------------------------------- #


class RetrievalRequest(BaseModel):
    """Retrieve relevant chunks without generating an answer."""

    query: str = Field(
        min_length=1,
        max_length=4000,
    )

    document_id: UUID | None = None

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )


class RetrievalChunk(BaseModel):
    """Single retrieved chunk."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID

    document_id: UUID

    chunk_index: int

    content: str

    similarity_score: float

    metadata: dict = Field(
        default_factory=dict,
    )


class RetrievalResponse(BaseModel):
    """Semantic retrieval response."""

    retrieved_chunks: int

    results: list[RetrievalChunk]


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #


class RAGHealthResponse(BaseModel):
    """Health status of the RAG subsystem."""

    status: str

    embedding_provider: str

    vector_store: str

    llm_provider: str