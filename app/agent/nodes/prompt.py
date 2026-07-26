"""
app/agent/nodes/prompt.py

Prompt construction node for the LangGraph AI Agent.

Responsibilities
----------------
- Load and render the active system prompt
- Build the final LLM prompt
- Combine conversation history with retrieved context
- Store the prompt in the graph state
"""

from __future__ import annotations

from app.agent.builders.prompt_builder import PromptBuilder
from app.agent.state import AgentState
from app.services.llm.prompt_manager import PromptManager
from app.agent.prompts.system_prompt import get_system_prompt


async def prompt_node(
    state: AgentState,
    *,
    prompt_builder: PromptBuilder,
    prompt_manager: PromptManager,
) -> AgentState:
    """
    Build the final prompt for the LLM.
    """

    system_prompt = await prompt_manager.render_prompt(
        org_id=state["org_id"],
        name="crm_chat",
        variables={
            "conversation_history": state.get("messages", []),
            "retrieved_context": state.get("retrieved_documents", []),
            "user_query": state["query"],
        },
    )

    if system_prompt is None:
        system_prompt = get_system_prompt()

    state["prompt"] = prompt_builder.build(
        system_prompt=system_prompt,
        query=state["query"],
        messages=state.get("messages", []),
        documents=state.get("retrieved_documents", []),
    )

    return state