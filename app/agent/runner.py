"""
app/agent/runner.py

Executes the compiled LangGraph workflow.
"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from app.agent.graph import get_agent_graph
from app.agent.state import AgentState
from app.observability.tracing import trace_context, traced


class AgentRunner:
    """
    Executes the compiled LangGraph agent.
    """

    def __init__(
        self,
        graph: CompiledStateGraph | None = None,
    ) -> None:
        self._graph = graph or get_agent_graph()

    @property
    def graph(self) -> CompiledStateGraph:
        """
        Expose the compiled graph.
        """
        return self._graph

    @traced(
        name="crm-agent",
        run_type="chain",
        tags=["agent", "langgraph"],
    )
    async def run(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Execute the LangGraph workflow.
        """

        with trace_context(
            metadata={
                "tenant_id": (
                    str(state["tenant_id"])
                    if state.get("tenant_id")
                    else None
                ),
                "org_id": (
                    str(state["org_id"])
                    if state.get("org_id")
                    else None
                ),
                "user_id": (
                    str(state["user_id"])
                    if state.get("user_id")
                    else None
                ),
                "conversation_id": (
                    str(state["conversation_id"])
                    if state.get("conversation_id")
                    else None
                ),
                "component": "agent",
                "framework": "langgraph",
            },
            tags=[
                "agent",
                "langgraph",
                "crm-copilot",
            ],
        ):
            return await self._graph.ainvoke(state)