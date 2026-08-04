from __future__ import annotations

from app.agent.state import AgentState
from app.observability.tracing import traced
from app.rag.chains.rag_chain import RAGChain


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
    print("=" * 80)
    print("GENERATE NODE")
    print("Documents passed to RAG:", len(state["retrieved_documents"]))

    for i, doc in enumerate(state["retrieved_documents"]):
        print(f"{i}: {doc.metadata.get('filename')}")

    print("=" * 80)
    
    result = await rag_chain.run(
        query=state["query"],
        documents=state["retrieved_documents"],
        prompt=state["prompt"],
    )

    state["response"] = result.response
    state["usage"] = result.usage
    state["finish_reason"] = result.finish_reason

    return state