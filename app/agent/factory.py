from __future__ import annotations

from app.agent.builders.graph_builder import GraphBuilder
from app.agent.builders.prompt_builder import PromptBuilder
from app.services.llm.prompt_manager import PromptManager
from app.agent.runner import AgentRunner
from app.agent.service import AgentService
from app.rag.chains.rag_chain import RAGChain
from app.rag.retrieval_service import RetrievalService


class AgentFactory:
    """
    Factory responsible for constructing the AI Agent.
    """

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        prompt_builder: PromptBuilder,
        rag_chain: RAGChain,
        prompt_manager: PromptManager,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.prompt_builder = prompt_builder
        self.prompt_manager = prompt_manager
        self.rag_chain = rag_chain

    def build(self) -> AgentService:
        """
        Construct the complete AgentService.
        """

        graph = GraphBuilder(
            retrieval_service=self.retrieval_service,
            prompt_builder=self.prompt_builder,
            prompt_manager=self.prompt_manager,
            rag_chain=self.rag_chain,
        ).build()

        runner = AgentRunner(graph=graph)

        return AgentService(runner=runner)


def build_agent(
    *,
    retrieval_service: RetrievalService,
    prompt_builder: PromptBuilder,
    prompt_manager: PromptManager,
    rag_chain: RAGChain,
) -> AgentService:
    """
    Convenience factory function used by dependency injection.
    """

    return AgentFactory(
        retrieval_service=retrieval_service,
        prompt_builder=prompt_builder,
        prompt_manager=prompt_manager,
        rag_chain=rag_chain,
    ).build()