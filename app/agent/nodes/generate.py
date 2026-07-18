"""
app/agent/nodes/generate.py

Generation node for the LangGraph AI Agent.

Responsibilities
----------------
- Execute the RAGChain
- Generate the final AI response
- Store token usage statistics

This node does NOT:
- Retrieve documents
- Build prompts
- Extract citations
- Stream responses
"""

from __future__ import annotations

from app.agent.state import AgentState
from app.rag.chains.rag_chain import RAGChain


async def generate_node(
    state: AgentState,
    *,
    rag_chain: RAGChain,
) -> AgentState:
    """
    Execute the RAGChain and store the generated response.
    """

    result = await rag_chain.run(
        query=state["query"],
        documents=state["retrieved_documents"],
        prompt=state["prompt"],
    )

    state["response"] = result.response
    state["usage"] = result.usage

    return state