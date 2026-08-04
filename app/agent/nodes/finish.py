from __future__ import annotations

from app.agent.state import AgentState
from app.agent.utils.citations import build_citations
from app.observability.tracing import traced


@traced(
    name="finish-node",
    run_type="chain",
    tags=["agent", "finish"],
)
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