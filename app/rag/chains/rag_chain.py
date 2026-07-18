"""
app/rag/chains/rag_chain.py

RAG generation chain.

Responsibilities
----------------
- Build prompt from retrieved documents
- Invoke the configured LLM provider
- Return generated answer together with retrieval metadata

Retrieval is handled by RetrievalService.
Persistence, observability, and conversation management belong to the
service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.documents import Document

from app.rag.exceptions import RAGGenerationError
from app.rag.retrievers.retriever import RetrievalResult
from app.services.llm.base import LLMProvider

from app.services.llm.models import TokenUsage


@dataclass(slots=True)
class RAGResult:
    """
    Result returned by the RAG chain.

    Used by the AI Agent.
    """

    response: str

    documents: list[Document] = field(default_factory=list)

    similarity_scores: list[float] = field(default_factory=list)

    usage: TokenUsage = field(
        default_factory=TokenUsage.empty,
    )

    finish_reason: str = "stop"



# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class RAGResponse:
    """Response returned from the RAG pipeline."""

    answer: str
    documents: list[Document]
    similarity_scores: list[float]


# --------------------------------------------------------------------------- #
# Chain
# --------------------------------------------------------------------------- #


class RAGChain:
    """
    Generates answers from already retrieved documents.

    Retrieval is intentionally delegated to RetrievalService.
    """

    def __init__(
        self,
        *,
        provider: LLMProvider,
    ) -> None:
        self.provider = provider

    # ------------------------------------------------------------------ #
    # Generate
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        *,
        query: str,
        retrieval_result: RetrievalResult,
    ) -> RAGResponse:
        """
        Generate an answer from retrieved documents.
        """

        if not query.strip():
            raise RAGGenerationError(
                "Query cannot be empty."
            )

        try:
            context = self._build_context(
                retrieval_result.documents,
            )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful CRM AI assistant.\n\n"
                        "Answer ONLY using the provided context.\n"
                        "If the answer cannot be found in the context, "
                        'say "I could not find that information in the knowledge base."'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context}\n\n"
                        f"Question:\n{query}"
                    ),
                },
            ]

            answer = await self.provider.complete(
                messages=messages,
            )

            return RAGResponse(
                answer=answer,
                documents=retrieval_result.documents,
                similarity_scores=retrieval_result.similarity_scores,
            )

        except Exception as exc:
            raise RAGGenerationError(
                "Failed to generate RAG response."
            ) from exc
        

    # ------------------------------------------------------------------ #
    # Run
    # ------------------------------------------------------------------ #
        
    async def run(
        self,
        *,
        query: str,
        documents: list[Document],
        prompt: str | None = None,
    ) -> RAGResult:

        retrieval_result = RetrievalResult(
            documents=documents,
            similarity_scores=[],
            retrieval_metadata={},
        )

        rag_response = await self.generate(
            query=query,
            retrieval_result=retrieval_result,
        )

        return RAGResult(
            response=rag_response.answer,
            documents=rag_response.documents,
            similarity_scores=rag_response.similarity_scores,
            usage=TokenUsage.empty(),
            finish_reason="stop",
        )

    # ------------------------------------------------------------------ #
    # Stream
    # ------------------------------------------------------------------ #

    async def stream(
        self,
        *,
        query: str,
        retrieval_result: RetrievalResult,
    ):
        """
        Stream an answer from retrieved documents.
        """

        if not query.strip():
            raise RAGGenerationError(
                "Query cannot be empty."
            )

        context = self._build_context(
            retrieval_result.documents,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful CRM AI assistant.\n\n"
                    "Answer ONLY using the provided context.\n"
                    "If the answer cannot be found in the context, "
                    'say "I could not find that information in the knowledge base."'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question:\n{query}"
                ),
            },
        ]

        async for chunk in self.provider.stream(
            messages=messages,
        ):
            yield chunk

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_context(
        documents: list[Document],
    ) -> str:
        """
        Convert retrieved documents into prompt context.
        """

        if not documents:
            return "No relevant context found."

        blocks: list[str] = []

        for index, document in enumerate(
            documents,
            start=1,
        ):
            title = (
                document.metadata.get("title")
                or document.metadata.get("filename")
                or f"Document {index}"
            )

            blocks.append(
                f"[{index}] {title}\n"
                f"{document.page_content}"
            )

        return "\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def build_rag_chain(
    *,
    provider: LLMProvider,
) -> RAGChain:
    """
    Factory for dependency injection.
    """

    return RAGChain(
        provider=provider,
    )