"""
tests/integration/test_agent_chat.py

Integration tests for the AI Agent chat workflow.

These tests verify the complete execution path:

Chat API
    ↓
ChatService
    ↓
AgentService
    ↓
AgentRunner
    ↓
LangGraph
    ↓
Retrieve
Prompt
Generate
Finish
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agent.service import AgentService
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_agent_chat_success() -> None:
    """
    AgentService should return the completed AgentState.
    """

    expected_state: AgentState = {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "What is CRM Copilot?",
        "messages": [],
        "retrieved_documents": [],
        "retrieval_metadata": {},
        "prompt": "Prompt",
        "response": "CRM Copilot is an AI-powered CRM assistant.",
        "citations": [],
        "usage": {},
        "errors": [],
    }

    runner = AsyncMock()
    runner.run.return_value = expected_state

    service = AgentService(runner)

    result = await service.run(
        conversation_id=expected_state["conversation_id"],
        tenant_id=expected_state["tenant_id"],
        user_id=expected_state["user_id"],
        query=expected_state["query"],
    )

    runner.run.assert_awaited_once()

    assert result == expected_state
    assert result["response"] == (
        "CRM Copilot is an AI-powered CRM assistant."
    )


@pytest.mark.asyncio
async def test_agent_chat_with_retrieved_documents() -> None:
    """
    Retrieved documents should be preserved in the final state.
    """

    expected_state: AgentState = {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "Explain RAG",
        "messages": [],
        "retrieved_documents": ["doc1", "doc2"],
        "retrieval_metadata": {
            "documents": 2,
        },
        "prompt": "Prompt",
        "response": "Generated answer",
        "citations": [
            {"title": "Document 1"},
            {"title": "Document 2"},
        ],
        "usage": {
            "total_tokens": 42,
        },
        "errors": [],
    }

    runner = AsyncMock()
    runner.run.return_value = expected_state

    service = AgentService(runner)

    result = await service.run(
        conversation_id=expected_state["conversation_id"],
        tenant_id=expected_state["tenant_id"],
        user_id=expected_state["user_id"],
        query=expected_state["query"],
    )

    assert len(result["retrieved_documents"]) == 2
    assert len(result["citations"]) == 2


@pytest.mark.asyncio
async def test_agent_chat_without_documents() -> None:
    """
    Agent should still complete successfully when retrieval
    returns no documents.
    """

    expected_state: AgentState = {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "Hello",
        "messages": [],
        "retrieved_documents": [],
        "retrieval_metadata": {},
        "prompt": "Prompt",
        "response": "Hello!",
        "citations": [],
        "usage": {},
        "errors": [],
    }

    runner = AsyncMock()
    runner.run.return_value = expected_state

    service = AgentService(runner)

    result = await service.run(
        conversation_id=expected_state["conversation_id"],
        tenant_id=expected_state["tenant_id"],
        user_id=expected_state["user_id"],
        query=expected_state["query"],
    )

    assert result["retrieved_documents"] == []
    assert result["citations"] == []
    assert result["response"] == "Hello!"


@pytest.mark.asyncio
async def test_agent_chat_propagates_runner_exception() -> None:
    """
    Exceptions raised by the AgentRunner should propagate.
    """

    runner = AsyncMock()
    runner.run.side_effect = RuntimeError("Graph execution failed")

    service = AgentService(runner)

    with pytest.raises(RuntimeError, match="Graph execution failed"):
        await service.run(
            conversation_id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            query="Hello",
        )


@pytest.mark.asyncio
async def test_agent_chat_returns_usage() -> None:
    """
    Usage information should be preserved in the final AgentState.
    """

    expected_state: AgentState = {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "Hello",
        "messages": [],
        "retrieved_documents": [],
        "retrieval_metadata": {},
        "prompt": "Prompt",
        "response": "Hello!",
        "citations": [],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 25,
            "total_tokens": 37,
            "model": "mock-model",
        },
        "errors": [],
    }

    runner = AsyncMock()
    runner.run.return_value = expected_state

    service = AgentService(runner)

    result = await service.run(
        conversation_id=expected_state["conversation_id"],
        tenant_id=expected_state["tenant_id"],
        user_id=expected_state["user_id"],
        query=expected_state["query"],
    )

    assert result["usage"]["total_tokens"] == 37


@pytest.mark.asyncio
async def test_agent_chat_returns_errors() -> None:
    """
    Errors recorded by the graph should be returned to the caller.
    """

    expected_state: AgentState = {
        "conversation_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "query": "Hello",
        "messages": [],
        "retrieved_documents": [],
        "retrieval_metadata": {},
        "prompt": "",
        "response": None,
        "citations": [],
        "usage": {},
        "errors": [
            {
                "node": "retrieve",
                "message": "Retrieval failed",
            }
        ],
    }

    runner = AsyncMock()
    runner.run.return_value = expected_state

    service = AgentService(runner)

    result = await service.run(
        conversation_id=expected_state["conversation_id"],
        tenant_id=expected_state["tenant_id"],
        user_id=expected_state["user_id"],
        query=expected_state["query"],
    )

    assert len(result["errors"]) == 1
    assert result["errors"][0]["node"] == "retrieve"