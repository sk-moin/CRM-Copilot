"""
app/agent/service.py

High-level AI Agent service.

Responsibilities
----------------
- Provide a simple interface for executing the LangGraph agent
- Build the initial AgentState
- Invoke the AgentRunner
- Return the completed AgentState

This service does NOT:
- Perform retrieval
- Build prompts
- Call the LLM directly
- Persist conversations

Those responsibilities belong to the LangGraph nodes and the existing
RAG infrastructure.
"""

from __future__ import annotations

from uuid import UUID

from app.agent.runner import AgentRunner
from app.agent.state import AgentState


class AgentService:
    """
    High-level service responsible for executing the AI Agent.
    """

    def __init__(
        self,
        runner: AgentRunner,
    ) -> None:
        self.runner = runner

    async def run(
        self,
        *,
        conversation_id: UUID,
        tenant_id: UUID,
        user_id: UUID | None,
        query: str,
    ) -> AgentState:

    

        initial_state: AgentState = {
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "query": query,

            "messages": [],
            "retrieved_documents": [],
            "retrieval_metadata": {},

            "prompt": "",
            "response": None,

            "citations": [],
            "usage": {},
            "errors": [],
        }

        return await self.runner.run(initial_state)