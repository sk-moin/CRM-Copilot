"""
app/rag/retrieval_service.py

High-level retrieval service.

Responsibilities
----------------
- Execute semantic retrieval
- Measure retrieval performance
- Persist retrieval traces
- Persist retrieved chunks
- Return retrieval results

This service does NOT:
- generate answers
- call the LLM
- build prompts

Those responsibilities belong to RAGChain.
"""

from __future__ import annotations

import time
from uuid import UUID
import logging
from functools import lru_cache

from app.rag.retrievers.retriever import (
    RetrievalResult,
    Retriever,
)
from app.rag.rerankers.langchain_reranker import LangChainReranker
from packages.database.models.retrieval_trace import (
    RetrievalTraceStatus,
)
from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)
from app.observability.tracing import traced, trace_context
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_default_reranker() -> LangChainReranker:
    """Return the process-wide reranker.

    Constructing a LangChainReranker loads a cross-encoder model into memory.
    RetrievalService is built per request by an uncached FastAPI dependency, so
    without this cache every concurrent chat request loads its own copy of the
    model. The load stays lazy: nothing happens until the first rerank.
    """

    return LangChainReranker(top_n=5)

class RetrievalService:
    """
    High-level semantic retrieval service.
    """

    def __init__(
        self,
        *,
        retriever: Retriever,
        retrieval_trace_repository: RetrievalTraceRepository,
        retrieved_chunk_repository: RetrievedChunkRepository,
        reranker: LangChainReranker | None = None,
    ) -> None:
        self.retriever = retriever
        self.trace_repository = retrieval_trace_repository
        self.chunk_repository = retrieved_chunk_repository
        self._reranker = reranker


    @property
    def reranker(self) -> LangChainReranker:
        if self._reranker is None:
            self._reranker = get_default_reranker()
        return self._reranker

    @traced(
        name="semantic-retrieval",
        run_type="retriever",
        tags=["retrieval", "rag", "crm-copilot"],
    )
    async def retrieve(
        self,
        *,
        conversation_id: UUID | None,
        query: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        document_id: UUID | None = None,
    ) -> RetrievalResult:
        """
        Execute semantic retrieval and record observability data.
        """

        trace = await self.trace_repository.create(
            conversation_id=conversation_id,
            query=query,
        )

        started_at = time.perf_counter()

        retrieval_metadata: dict[str, object] = {}

        settings = get_settings()

        try:
            with trace_context(
                metadata={
                    "conversation_id": str(conversation_id)
                    if conversation_id
                    else None,
                    "document_id": str(document_id)
                    if document_id
                    else None,
                    "query": query,
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "component": "retrieval",
                    "framework": "langchain",
                    "environment": settings.ENVIRONMENT,
                },
                tags=[
                    "retrieval",
                    "rag",
                    "crm-copilot",
                ],
            ):
                result = await self.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    document_id=document_id,
                )

                # -------------------------------------------------
                # Remove duplicate chunks while preserving scores
                # -------------------------------------------------

                seen = set()
                unique_docs = []
                unique_scores = []

                for doc, score in zip(
                    result.documents,
                    result.similarity_scores,
                ):

                    key = (
                        doc.metadata.get("document_id"),
                        doc.metadata.get("chunk_index"),
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    unique_docs.append(doc)
                    unique_scores.append(score)

                result.documents = unique_docs
                result.similarity_scores = unique_scores

                logger.debug(
                    "Retrieval completed",
                    extra={
                        "requested_top_k": top_k,
                        "after_dedup": len(result.documents),
                    },
                )

                # Preserve vector similarity scores before reranking
                score_map = {
                    doc.metadata["chunk_id"]: score
                    for doc, score in zip(
                        result.documents,
                        result.similarity_scores,
                    )
                }

                reranked_docs = self.reranker.rerank(
                    query=query,
                    documents=result.documents,
                )


                reranked_scores = [
                    score_map.get(
                        doc.metadata["chunk_id"],
                        0.0,
                    )
                    for doc in reranked_docs
                ]

                result.documents = reranked_docs
                result.similarity_scores = reranked_scores

            latency_ms = int(
                (time.perf_counter() - started_at) * 1000
            )

            retrieval_metadata = dict(result.retrieval_metadata)

            retrieval_metadata.update(
                {
                    "latency_ms": latency_ms,
                    "retrieved_chunks": result.retrieved_chunks,
                    "embedding_provider": settings.EMBEDDING_PROVIDER,
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "vector_store": "pgvector",
                    "chunk_ids": [
                        str(doc.metadata["chunk_id"])
                        for doc in result.documents
                        if "chunk_id" in doc.metadata
                    ],
                }
            )

            await self.trace_repository.update_metrics(
                trace.id,
                retrieval_latency_ms=latency_ms,
                total_latency_ms=latency_ms,
                embedding_model=settings.EMBEDDING_MODEL,
                vector_store="pgvector",
                retrieved_chunk=result.retrieved_chunks,
                retrieval_metadata=retrieval_metadata,
            )

            await self.trace_repository.update_status(
                trace.id,
                status=RetrievalTraceStatus.SUCCESS,
            )

            retrieved_chunks_payload: list[dict] = []

            for rank, (document, score) in enumerate(
                zip(
                    result.documents,
                    result.similarity_scores,
                ),
                start=1,
            ):
                metadata = document.metadata

                chunk_id = metadata.get("chunk_id")
                document_id = metadata.get("document_id")

                if chunk_id is None or document_id is None:
                    continue

                retrieved_chunks_payload.append(
                    {
                        "trace_id": trace.id,
                        "document_id": UUID(document.metadata["document_id"]),
                        "chunk_id": UUID(document.metadata["chunk_id"]),
                        "rank": rank,
                        "similarity_score": score,
                        "chunk_preview": document.page_content[:500],
                        "retrieval_metadata": {},
                    }
                )

            if retrieved_chunks_payload:

                logger.debug(
                    "Persisting retrieved chunks",
                    extra={
                        "trace_id": str(trace.id),
                        "chunk_count": len(retrieved_chunks_payload),
                    },
                )

                await self.chunk_repository.bulk_create(
                    retrieved_chunks_payload,
                )

            return result

        except Exception as exc:
            latency_ms = int(
                (time.perf_counter() - started_at) * 1000
            )

            retrieval_metadata.update(
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

            await self.trace_repository.update_metrics(
                trace.id,
                retrieval_latency_ms=latency_ms,
                total_latency_ms=latency_ms,
                retrieval_metadata=retrieval_metadata,
            )

            await self.trace_repository.update_status(
                trace.id,
                status=RetrievalTraceStatus.FAILED,
                error_message=str(exc),
            )

            raise


    

        