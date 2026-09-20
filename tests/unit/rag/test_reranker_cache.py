"""The cross-encoder reranker must be loaded once per process, not per request.

`get_retrieval_service` is an ordinary uncached FastAPI dependency, so a new
`RetrievalService` is built for every chat request. Constructing a
`LangChainReranker` loads a cross-encoder model into memory, so without a
module-level cache N concurrent requests load N copies of the model.

These tests patch the reranker class so nothing real is loaded.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import app.rag.retrieval_service as retrieval_service
from app.rag.retrieval_service import RetrievalService


@pytest.fixture(autouse=True)
def _clear_reranker_cache():
    """Isolate each test from the process-wide cache, before and after."""

    retrieval_service.get_default_reranker.cache_clear()
    yield
    retrieval_service.get_default_reranker.cache_clear()


def _service() -> RetrievalService:
    return RetrievalService(
        retriever=None,
        retrieval_trace_repository=None,
        retrieved_chunk_repository=None,
    )


def test_separate_services_share_one_reranker() -> None:
    with patch.object(retrieval_service, "LangChainReranker") as reranker_cls:
        reranker_cls.return_value = object()

        first = _service().reranker
        second = _service().reranker

        assert first is second
        assert reranker_cls.call_count == 1, (
            "The cross-encoder was constructed more than once; each "
            "construction loads a full copy of the model into memory."
        )


def test_reranker_is_not_loaded_until_first_use() -> None:
    """The load stays lazy — building the service must not touch the model."""

    with patch.object(retrieval_service, "LangChainReranker") as reranker_cls:
        _service()

        assert reranker_cls.call_count == 0


def test_an_injected_reranker_is_respected() -> None:
    """An explicitly supplied reranker must win over the shared default."""

    injected = object()

    with patch.object(retrieval_service, "LangChainReranker") as reranker_cls:
        service = RetrievalService(
            retriever=None,
            retrieval_trace_repository=None,
            retrieved_chunk_repository=None,
            reranker=injected,
        )

        assert service.reranker is injected
        assert reranker_cls.call_count == 0
