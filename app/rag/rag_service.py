"""
app/rag/rag_service.py

High-level Retrieval-Augmented Generation service.

Responsibilities
----------------
- Execute Retrieval-Augmented Generation
- Execute streaming Retrieval-Augmented Generation
- Orchestrate RetrievalService and RAGChain

This service intentionally does NOT:
- process documents
- generate embeddings
- perform vector search directly
- persist retrieval traces
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from app.rag.chains.rag_chain import (
    RAGChain,
    RAGResponse,
)
from app.rag.exceptions import (
    RAGGenerationError,
    RetrievalError,
)
from app.rag.retrieval_service import RetrievalService
from app.rag.retrievers.retriever import RetrievalResult
from app.services.llm.models import StreamChunk


class RAGService:
    """
    High-level facade for Retrieval-Augmented Generation.

    Coordinates retrieval and answer generation while hiding the
    implementation details from API routes.
    """

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        rag_chain: RAGChain,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.rag_chain = rag_chain

    # ------------------------------------------------------------------ #
    # RAG
    # ------------------------------------------------------------------ #

    async def ask(
        self,
        *,
        conversation_id: UUID | None,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        document_id: UUID | None = None,
    ) -> RAGResponse:
        """
        Execute a complete Retrieval-Augmented Generation workflow.
        """

        try:
            retrieval_result = await self.retrieval_service.retrieve(
                conversation_id=conversation_id,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_id=document_id,
            )

            return await self.rag_chain.generate(
                query=query,
                retrieval_result=retrieval_result,
            )

        except RAGGenerationError:
            raise

        except Exception as exc:
            raise RAGGenerationError(
                "Failed to generate RAG response."
            ) from exc

    async def stream(
        self,
        *,
        conversation_id: UUID | None,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        document_id: UUID | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute a streaming Retrieval-Augmented Generation workflow.
        """

        try:
            retrieval_result = await self.retrieval_service.retrieve(
                conversation_id=conversation_id,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_id=document_id,
            )

            stream = self.rag_chain.stream(
                query=query,
                retrieval_result=retrieval_result,
            )

            async for chunk in stream:
                yield chunk

        except RAGGenerationError:
            raise

        except Exception as exc:
            raise RAGGenerationError(
                "Failed to generate streaming RAG response."
            ) from exc

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    async def retrieve(
        self,
        *,
        conversation_id: UUID | None,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        document_id: UUID | None = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents without invoking the LLM.
        """

        try:
            return await self.retrieval_service.retrieve(
                conversation_id=conversation_id,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_id=document_id,
            )

        except RetrievalError:
            raise

        except Exception as exc:
            raise RetrievalError(
                "Failed to retrieve documents."
            ) from exc