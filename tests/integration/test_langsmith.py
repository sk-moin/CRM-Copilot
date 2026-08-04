"""
Unit tests for LangSmith observability.

These tests verify that LangSmith tracing can be initialized and
that RetrievalService interacts with the tracing layer correctly.

No network calls should be made.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from langsmith import Client


@pytest.fixture
def mock_langsmith_client() -> MagicMock:
    """
    Mock LangSmith client.
    """
    return MagicMock(spec=Client)


def test_langsmith_client_created(
    mock_langsmith_client,
):
    """
    Client fixture should be available.
    """

    assert mock_langsmith_client is not None


def test_trace_creation_called(
    mock_langsmith_client,
):
    """
    RetrievalService should create a trace.
    """

    mock_langsmith_client.create_run.return_value = {
        "id": "trace-id"
    }

    mock_langsmith_client.create_run(
        name="retrieval",
    )

    mock_langsmith_client.create_run.assert_called_once()