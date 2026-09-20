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
from app.observability.tracing import traced
from app.observability.tracing import trace_context

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
    answer: str
    documents: list[Document]
    similarity_scores: list[float]
    usage: TokenUsage = field(default_factory=TokenUsage.empty)
    finish_reason: str = "stop"


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

    @traced(
        name="rag-generate",
        run_type="chain",
    )

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

            

            with trace_context(
                metadata={
                    "llm_provider": type(self.provider).__name__,
                    "retrieved_chunks": retrieval_result.retrieved_chunks,
                    "document_count": len(retrieval_result.documents),
                },
                tags=[
                    "rag",
                    "generation",
                ],
            ):
                completion = await self.provider.complete(
                    messages=messages,
                )

            return RAGResponse(
                answer=completion.content,
                documents=retrieval_result.documents,
                similarity_scores=retrieval_result.similarity_scores,
                usage=completion.usage,
                finish_reason=completion.finish_reason,
            )

        except Exception as exc:
            raise RAGGenerationError(
                "Failed to generate RAG response."
            ) from exc
        

    # ------------------------------------------------------------------ #
    # Run
    # ------------------------------------------------------------------ #
    @traced(
        name="rag-chain",
        run_type="chain",
    )
    async def run(
        self,
        *,
        query: str,
        documents: list[Document],
        prompt: str | None = None,
    ) -> RAGResult:
        """
        Execute the RAG chain.

        NOTE:
        The prompt parameter is currently ignored because prompt construction
        happens inside generate(). It is kept only for future compatibility.
        """

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
            usage=rag_response.usage,
            finish_reason=rag_response.finish_reason,
        )

    # ------------------------------------------------------------------ #
    # Stream
    # ------------------------------------------------------------------ #
    @traced(
        name="rag-stream",
        run_type="chain",
    )
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

        with trace_context(
            metadata={
                "llm_provider": type(self.provider).__name__,
                "retrieved_chunks": retrieval_result.retrieved_chunks,
                "document_count": len(retrieval_result.documents),
            },
            tags=[
                "rag",
                "stream",
            ],
        ):
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
        if not documents:
            return "No relevant context found."

        seen = set()
        blocks = []

        for document in documents:
            content = document.page_content.strip()

            if content in seen:
                continue

            seen.add(content)

            title = (
                document.metadata.get("title")
                or document.metadata.get("filename")
                or "Document"
            )

            blocks.append(
                f"[Source {len(blocks)+1}] {title}\n"
                f"{content}"
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