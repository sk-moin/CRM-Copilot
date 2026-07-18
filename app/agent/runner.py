"""
app/agent/runner.py

Runner for the CRM Copilot LangGraph agent.

Responsibilities
----------------
- Build the initial AgentState
- Execute the LangGraph workflow
- Return the final AgentState

Business logic belongs inside graph nodes.
"""

from __future__ import annotations

from uuid import UUID

from app.agent.state import AgentState


class AgentRunner:
    """
    Executes the CRM Copilot LangGraph workflow.
    """

    def __init__(self, graph) -> None:
        self.graph = graph

    async def run(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Execute the AI agent workflow.

        Parameters
        ----------
        conversation_id:
            Conversation identifier.

        tenant_id:
            Tenant identifier.

        user_id:
            User identifier.

        query:
            Current user message.

        messages:
            Previous conversation history.

        Returns
        -------
        AgentState
            Final graph state.
        """

        

        return await self.graph.ainvoke(state)
