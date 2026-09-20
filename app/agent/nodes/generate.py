from __future__ import annotations

from app.agent.state import AgentState
from app.observability.tracing import traced
from app.rag.chains.rag_chain import RAGChain
import logging

logger = logging.getLogger(__name__)

@traced(
    name="generate-node",
    run_type="chain",
    tags=["agent", "generation"],
)
async def generate_node(
    state: AgentState,
    *,
    rag_chain: RAGChain,
) -> AgentState:
    """
    Execute the RAGChain and store the generated response.
    """
    logger.debug(
        "Generate node started",
        extra={
            "retrieved_document_count": len(state["retrieved_documents"]),
        },
    )

    for i, doc in enumerate(state["retrieved_documents"]):
        logger.debug("agent.generate.document", extra={"metadata": doc.metadata})

    
    result = await rag_chain.run(
        query=state["query"],
        documents=state["retrieved_documents"],
        prompt=state["prompt"],
    )

    state["response"] = result.response
    state["usage"] = result.usage
    state["finish_reason"] = result.finish_reason

    return state