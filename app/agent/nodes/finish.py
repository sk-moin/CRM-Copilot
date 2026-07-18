"""
app/agent/nodes/finish.py

Finalization node for the LangGraph AI Agent.

Responsibilities
----------------
- Prepare the final agent output
- Extract citations from retrieved documents
- Ensure the graph state is complete before returning

This node does NOT:
- Retrieve documents
- Build prompts
- Call the LLM
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.agent.utils.citations import build_citations


async def finish_node(state: AgentState) -> AgentState:
    """
    Finalize the agent state before graph completion.
    """

    retrieved_documents = state.get("retrieved_documents", [])

    state["citations"] = build_citations(
        retrieved_documents,
    )

    state.setdefault("response", None)
    state.setdefault("usage", {})
    state.setdefault("errors", [])

    return state