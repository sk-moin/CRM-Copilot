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
        action_service_factory=None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.prompt_builder = prompt_builder
        self.prompt_manager = prompt_manager
        self.rag_chain = rag_chain
        self.action_service_factory = action_service_factory

    def build(self) -> AgentService:
        """
        Construct the complete AgentService.
        """

        graph = GraphBuilder(
            retrieval_service=self.retrieval_service,
            prompt_builder=self.prompt_builder,
            prompt_manager=self.prompt_manager,
            rag_chain=self.rag_chain,
            action_service_factory=self.action_service_factory,
        ).build()

        runner = AgentRunner(graph=graph)

        return AgentService(runner=runner)


def build_agent(
    *,
    retrieval_service: RetrievalService,
    prompt_builder: PromptBuilder,
    prompt_manager: PromptManager,
    rag_chain: RAGChain,
    action_service_factory=None,
) -> AgentService:
    """
    Convenience factory function used by dependency injection.
    """

    return AgentFactory(
        retrieval_service=retrieval_service,
        prompt_builder=prompt_builder,
        prompt_manager=prompt_manager,
        rag_chain=rag_chain,
        action_service_factory=action_service_factory,
    ).build()