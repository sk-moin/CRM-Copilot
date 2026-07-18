"""
tests/agent/test_agent_service.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agent.service import AgentService
from app.agent.state import AgentState


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def runner() -> AsyncMock:
    """
    Mock AgentRunner.
    """
    return AsyncMock()


@pytest.fixture
def service(
    runner: AsyncMock,
) -> AgentService:
    """
    AgentService under test.
    """
    return AgentService(
        runner=runner,
    )


@pytest.fixture
def agent_state() -> AgentState:
    """
    Example AgentState returned by the runner.
    """
    return AgentState(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        query="What is CRM?",
        messages=[],
        retrieved_documents=[],
        retrieval_metadata={},
        prompt="Prompt",
        response="CRM stands for Customer Relationship Management.",
        citations=[],
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        errors=[],
    )


# --------------------------------------------------------------------------- #
# execute()
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_execute_success(
    service: AgentService,
    runner: AsyncMock,
    agent_state: AgentState,
):
    """
    AgentService should delegate execution to AgentRunner.
    """

    runner.run.return_value = agent_state

    result = await service.run(
        conversation_id=agent_state["conversation_id"],
        tenant_id=agent_state["tenant_id"],
        user_id=agent_state["user_id"],
        query=agent_state["query"],
    )

    runner.run.assert_awaited_once()

    passed_state = runner.run.await_args.args[0]

    assert passed_state["conversation_id"] == agent_state["conversation_id"]
    assert passed_state["tenant_id"] == agent_state["tenant_id"]
    assert passed_state["user_id"] == agent_state["user_id"]
    assert passed_state["query"] == agent_state["query"]

    assert result == agent_state


@pytest.mark.asyncio
async def test_execute_without_user(
    service: AgentService,
    runner: AsyncMock,
    agent_state: AgentState,
):
    """
    System executions may not have a user_id.
    """

    agent_state["user_id"] = None

    runner.run.return_value = agent_state

    result = await service.run(
        conversation_id=agent_state["conversation_id"],
        tenant_id=agent_state["tenant_id"],
        user_id=None,
        query=agent_state["query"],
    )

    assert result["user_id"] is None


@pytest.mark.asyncio
async def test_execute_preserves_response(
    service: AgentService,
    runner: AsyncMock,
    agent_state: AgentState,
):
    """
    Response should be returned unchanged.
    """

    runner.run.return_value = agent_state

    result = await service.run(
        conversation_id=agent_state["conversation_id"],
        tenant_id=agent_state["tenant_id"],
        user_id=agent_state["user_id"],
        query=agent_state["query"],
    )

    assert (
        result["response"]
        == "CRM stands for Customer Relationship Management."
    )


@pytest.mark.asyncio
async def test_execute_preserves_usage(
    service: AgentService,
    runner: AsyncMock,
    agent_state: AgentState,
):
    """
    Token usage should be preserved.
    """

    runner.run.return_value = agent_state

    result = await service.run(
        conversation_id=agent_state["conversation_id"],
        tenant_id=agent_state["tenant_id"],
        user_id=agent_state["user_id"],
        query=agent_state["query"],
    )

    assert result["usage"]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_execute_preserves_citations(
    service: AgentService,
    runner: AsyncMock,
    agent_state: AgentState,
):
    """
    Citations should pass through unchanged.
    """

    agent_state["citations"] = [
        {
            "chunk_id": str(uuid4()),
            "title": "CRM Guide",
        }
    ]

    runner.run.return_value = agent_state

    result = await service.run(
        conversation_id=agent_state["conversation_id"],
        tenant_id=agent_state["tenant_id"],
        user_id=agent_state["user_id"],
        query=agent_state["query"],
    )

    assert len(result["citations"]) == 1


@pytest.mark.asyncio
async def test_execute_runner_failure(
    service: AgentService,
    runner: AsyncMock,
):
    """
    Runner exceptions should propagate.
    """

    runner.run.side_effect = RuntimeError(
        "Graph execution failed."
    )

    with pytest.raises(RuntimeError):
        await service.run(
            conversation_id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            query="CRM",
        )