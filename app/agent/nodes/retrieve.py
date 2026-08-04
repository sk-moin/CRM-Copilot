from __future__ import annotations

from app.agent.state import AgentState
from app.observability.tracing import traced
from app.rag.retrieval_service import RetrievalService


@traced(
    name="retrieve-node",
    run_type="retriever",
    tags=["agent", "retrieval"],
)
async def retrieve_node(
    state: AgentState,
    *,
    retrieval_service: RetrievalService,
) -> AgentState:
    """
    Execute semantic retrieval.
    """

    try:
        result = await retrieval_service.retrieve(
            conversation_id=state["conversation_id"],
            query=state["query"],
        )

        print("=" * 80)
        print("RETRIEVE RESULT")
        print("documents:", len(result.documents))
        print("=" * 80)

        state["retrieved_documents"] = result.documents
        state["retrieval_metadata"] = result.retrieval_metadata

        print("Retriever returned:", len(result.documents))

    except Exception as exc:
        print("=" * 80)
        print("RETRIEVE NODE EXCEPTION")
        print(type(exc))
        print(exc)
        print("=" * 80)

        state.setdefault("errors", []).append(
            {
                "node": "retrieve",
                "message": str(exc),
            }
        )

        state["retrieved_documents"] = []
        state["retrieval_metadata"] = {}

    print("STATE DOCUMENT COUNT:", len(state["retrieved_documents"]))

    return state