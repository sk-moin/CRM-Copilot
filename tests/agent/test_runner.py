"""
tests/agent/test_runner.py

Unit tests for AgentRunner.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agent.runner import AgentRunner
from app.agent.state import AgentState


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def compiled_graph() -> AsyncMock:
    """
    Mock compiled LangGraph.
    """
    graph = AsyncMock()
    graph.ainvoke = AsyncMock()
    return graph


@pytest.fixture
def runner(compiled_graph: AsyncMock) -> AgentRunner:
    """
    Runner under test.
    """
    return AgentRunner(
        graph=compiled_graph,
    )


@pytest.fixture
def state() -> AgentState:
    """
    Example AgentState.
    """
    return {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "What is CRM?",
        "messages": [],
        "retrieved_documents": [],
        "retrieval_metadata": {},
        "prompt": "",
        "response": None,
        "citations": [],
        "usage": {},
        "errors": [],
    }


# --------------------------------------------------------------------------- #
# run()
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_run_success(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Runner should invoke the graph and return its output.
    """

    expected = dict(state)
    expected["response"] = "CRM stands for Customer Relationship Management."

    compiled_graph.ainvoke.return_value = expected

    result = await runner.run(state)

    compiled_graph.ainvoke.assert_awaited_once_with(state)

    assert result == expected


@pytest.mark.asyncio
async def test_run_preserves_state(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Returned state should contain original identifiers.
    """

    compiled_graph.ainvoke.return_value = state

    result = await runner.run(state)

    assert result["conversation_id"] == state["conversation_id"]
    assert result["tenant_id"] == state["tenant_id"]
    assert result["query"] == state["query"]


@pytest.mark.asyncio
async def test_run_graph_failure(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Graph exceptions should propagate.
    """

    compiled_graph.ainvoke.side_effect = RuntimeError(
        "Graph execution failed."
    )

    with pytest.raises(RuntimeError):
        await runner.run(state)


@pytest.mark.asyncio
async def test_run_empty_response(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Runner should allow graphs that return empty responses.
    """

    returned = dict(state)

    compiled_graph.ainvoke.return_value = returned

    result = await runner.run(state)

    assert result["response"] is None
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_run_with_errors(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Runner should return graph errors unchanged.
    """

    returned = dict(state)

    returned["errors"] = [
        {
            "type": "retrieval_error",
            "message": "Vector search failed.",
        }
    ]

    compiled_graph.ainvoke.return_value = returned

    result = await runner.run(state)

    assert len(result["errors"]) == 1
    assert (
        result["errors"][0]["type"]
        == "retrieval_error"
    )


@pytest.mark.asyncio
async def test_run_with_usage(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Usage metadata should be preserved.
    """

    returned = dict(state)

    returned["usage"] = {
        "prompt_tokens": 120,
        "completion_tokens": 45,
        "total_tokens": 165,
    }

    compiled_graph.ainvoke.return_value = returned

    result = await runner.run(state)

    assert result["usage"]["total_tokens"] == 165


@pytest.mark.asyncio
async def test_run_with_citations(
    runner: AgentRunner,
    compiled_graph: AsyncMock,
    state: AgentState,
):
    """
    Citations should pass through unchanged.
    """

    returned = dict(state)

    returned["citations"] = [
        {
            "document_id": str(uuid4()),
            "title": "CRM Guide",
        }
    ]

    compiled_graph.ainvoke.return_value = returned

    result = await runner.run(state)

    assert len(result["citations"]) == 1
    assert result["citations"][0]["title"] == "CRM Guide"