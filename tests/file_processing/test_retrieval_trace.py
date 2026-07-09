"""Tests for RetrievalTrace model."""

from uuid import uuid4

import pytest

from packages.database.models.retrieval_trace import RetrievalTraceStatus
from packages.database.models.retrieval_trace import RetrievalTrace


def test_create_retrieval_trace():
    """Test RetrievalTrace model creation."""

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="What is RAG?",
        status=RetrievalTraceStatus.SUCCESS,
        retrieved_chunks=0,
    )

    assert trace.query == "What is RAG?"
    assert trace.retrieved_chunks == 0
    assert trace.status == RetrievalTraceStatus.SUCCESS


def test_trace_defaults():
    """Test default values."""

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="Test query",
    )

    assert trace.query == "Test query"
    assert trace.retrieved_chunks is None
    assert trace.status is None
    assert trace.embedding_model is None
    assert trace.vector_store is None
    assert trace.error_message is None


def test_trace_failure_status():
    """Test failed retrieval trace."""

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="Failure",
        status=RetrievalTraceStatus.FAILED,
        error_message="Embedding failed",
    )

    assert trace.status == RetrievalTraceStatus.FAILED
    assert trace.error_message == "Embedding failed"


def test_trace_metadata():
    """Test metadata field."""

    metadata = {
        "top_k": 5,
        "score_threshold": 0.7,
    }

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="metadata",
        retrieval_metadata=metadata,
    )

    assert trace.retrieval_metadata == metadata


def test_trace_latency_fields():
    """Test latency fields."""

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="Latency",
        embedding_latency_ms=12.5,
        retrieval_latency_ms=24.8,
        total_latency_ms=37.3,
    )

    assert trace.embedding_latency_ms == 12.5
    assert trace.retrieval_latency_ms == 24.8
    assert trace.total_latency_ms == 37.3


def test_trace_relationship_defaults():
    """Relationship collections should initialize."""

    trace = RetrievalTrace(
        tenant_id=uuid4(),
        query="Relationships",
    )

    assert trace.retrieved_chunk_records == []