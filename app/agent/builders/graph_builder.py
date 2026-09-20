"""
app/agent/builders/graph_builder.py

Builder responsible for constructing the LangGraph workflow used by the
CRM Copilot AI Agent.

Responsibilities
----------------
- Register LangGraph nodes
- Wire runtime dependencies into nodes
- Define execution flow
- Compile the graph

The builder contains no business logic. Individual nodes implement
their own responsibilities.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.agent.builders.prompt_builder import PromptBuilder
from app.services.llm.prompt_manager import PromptManager
from app.agent.nodes.finish import finish_node
from app.agent.nodes.generate import generate_node
from app.agent.nodes.prompt import prompt_node
from app.agent.nodes.propose import propose_node
from app.agent.nodes.retrieve import retrieve_node
from app.agent.state import AgentState
from app.rag.chains.rag_chain import RAGChain
from app.rag.retrieval_service import RetrievalService


class GraphBuilder:
    """
    Builder for the CRM Copilot LangGraph workflow.
    """

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        prompt_builder: PromptBuilder,
        prompt_manager: PromptManager,
        rag_chain: RAGChain,
        action_service_factory=None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.prompt_builder = prompt_builder
        self.prompt_manager = prompt_manager
        self.rag_chain = rag_chain

        # Optional: when absent the propose node is inert, so the graph stays
        # usable anywhere there is no request-scoped session.
        self.action_service_factory = action_service_factory

    def build(self):
        """
        Construct and compile the LangGraph.

        Workflow

        START
          ↓
        retrieve
          ↓
        prompt
          ↓
        generate
          ↓
        finish
          ↓
         END
        """

        graph = StateGraph(AgentState)

        # ---------------------------------------------------------
        # Register nodes with injected dependencies
        # ---------------------------------------------------------

        graph.add_node(
            "retrieve",
            partial(
                retrieve_node,
                retrieval_service=self.retrieval_service,
            ),
        )

        graph.add_node(
            "prompt",
            partial(
                prompt_node,
                prompt_builder=self.prompt_builder,
                prompt_manager=self.prompt_manager,
            ),
        )

        graph.add_node(
            "generate",
            partial(
                generate_node,
                rag_chain=self.rag_chain,
            ),
        )

        graph.add_node(
            "propose",
            partial(
                propose_node,
                action_service_factory=self.action_service_factory,
            ),
        )

        graph.add_node(
            "finish",
            finish_node,
        )

        # ---------------------------------------------------------
        # Workflow
        # ---------------------------------------------------------

        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "prompt")
        graph.add_edge("prompt", "generate")
        graph.add_edge("generate", "propose")
        graph.add_edge("propose", "finish")
        graph.add_edge("finish", END)

        return graph.compile()