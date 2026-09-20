from __future__ import annotations

import logging

from app.agent.state import AgentState
from app.observability.tracing import traced
from app.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

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

        logger.debug(
            "Retriever completed",
            extra={"document_count": len(result.documents)},
        )

        state["retrieved_documents"] = result.documents
        state["retrieval_metadata"] = result.retrieval_metadata


    except Exception as exc:
        logger.exception("Retrieve node failed")

        state.setdefault("errors", []).append(
            {
                "node": "retrieve",
                "message": str(exc),
            }
        )

        state["retrieved_documents"] = []
        state["retrieval_metadata"] = {}

    logger.debug(
        "Retrieved documents stored in agent state",
        extra={
            "document_count": len(state["retrieved_documents"]),
        },
    )

    return state