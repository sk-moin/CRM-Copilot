"""
app/agent/nodes/prompt.py

Prompt construction node for the LangGraph AI Agent.

Responsibilities
----------------
- Build the final LLM prompt
- Combine conversation history with retrieved context
- Store the prompt in the graph state

This node does NOT:
- Retrieve documents
- Call the LLM
- Stream responses
"""

from __future__ import annotations

from app.agent.builders.prompt_builder import PromptBuilder
from app.agent.state import AgentState


async def prompt_node(
    state: AgentState,
    *,
    prompt_builder: PromptBuilder,
) -> AgentState:
    """
    Build the final prompt for the LLM.
    """


    state["prompt"] = prompt_builder.build(
        query=state["query"],
        messages=state.get("messages", []),
        documents=state.get("retrieved_documents", []),
    )

    return state