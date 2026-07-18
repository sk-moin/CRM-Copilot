"""
app/agent/nodes/retrieve.py

Retrieval node for the LangGraph AI Agent.

Responsibilities
----------------
- Execute semantic retrieval
- Populate the graph state with retrieved documents
- Store retrieval metadata
- Delegate retrieval observability to RetrievalService

This node does NOT:
- Build prompts
- Call the LLM
- Generate citations
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.rag.retrieval_service import RetrievalService


async def retrieve_node(
    state: AgentState,
    *,
    retrieval_service: RetrievalService,
) -> AgentState:
    """
    Execute semantic retrieval.

    RetrievalService automatically records RetrievalTrace and
    RetrievedChunk records, so this node only updates the graph state.
    """

    try:
        result = await retrieval_service.retrieve(
            conversation_id=state["conversation_id"],
            query=state["query"],
        )

        state["retrieved_documents"] = result.documents
        state["retrieval_metadata"] = result.retrieval_metadata

    except Exception as exc:
        state.setdefault("errors", []).append(
            {
                "node": "retrieve",
                "message": str(exc),
            }
        )

        state["retrieved_documents"] = []
        state["retrieval_metadata"] = {}

    return state