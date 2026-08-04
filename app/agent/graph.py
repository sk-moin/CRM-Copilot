"""
app/agent/graph.py

LangGraph orchestration for the CRM Copilot AI Agent.

Responsibilities
----------------
- Define the execution graph
- Register workflow nodes
- Compile the graph
- Expose a reusable compiled graph

Business logic lives inside individual nodes.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes.finish import finish_node
from app.agent.nodes.generate import generate_node
from app.agent.nodes.prompt import prompt_node
from app.agent.nodes.retrieve import retrieve_node
from app.agent.state import AgentState


class AgentGraph:
    """
    Builds the CRM Copilot LangGraph workflow.

    Workflow:

        START
           │
        retrieve
           │
         prompt
           │
        generate
           │
         finish
           │
          END
    """

    def build(self) -> CompiledStateGraph:
        """
        Build and compile the LangGraph workflow.
        """

        workflow = StateGraph(AgentState)

        # ------------------------------------------------------------------ #
        # Register nodes
        # ------------------------------------------------------------------ #

        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("prompt", prompt_node)
        workflow.add_node("generate", generate_node)
        workflow.add_node("finish", finish_node)

        # ------------------------------------------------------------------ #
        # Register edges
        # ------------------------------------------------------------------ #

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "prompt")
        workflow.add_edge("prompt", "generate")
        workflow.add_edge("generate", "finish")
        workflow.add_edge("finish", END)

        return workflow.compile()


_graph: CompiledStateGraph | None = None


def get_agent_graph() -> CompiledStateGraph:
    """
    Return a singleton compiled LangGraph instance.

    The graph is compiled only once during application lifetime.
    """

    global _graph

    if _graph is None:
        _graph = AgentGraph().build()

    return _graph