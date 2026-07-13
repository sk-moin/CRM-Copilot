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

from app.rag.retrievers.retriever import (
    RetrievalResult,
    Retriever,
)
from packages.database.models.retrieval_trace import (
    RetrievalTraceStatus,
)
from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)


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
    ) -> None:
        self.retriever = retriever
        self.trace_repository = retrieval_trace_repository
        self.chunk_repository = retrieved_chunk_repository

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
        Execute semantic retrieval and record observability data.
        """

        trace = await self.trace_repository.create(
            conversation_id=conversation_id,
            query=query,
        )

        started_at = time.perf_counter()

        try:
            result = await self.retriever.retrieve(
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_id=document_id,
            )

            latency_ms = int(
                (time.perf_counter() - started_at) * 1000
            )

            await self.trace_repository.update_metrics(
                trace.id,
                retrieval_latency_ms=latency_ms,
                total_latency_ms=latency_ms,
                retrieved_chunk=result.retrieved_chunks,
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
                chunk_id = document.metadata.get("chunk_id")

                if chunk_id is None:
                    continue

                retrieved_chunks_payload.append(
                    {
                        "retrieval_trace_id": trace.id,
                        "document_chunk_id": UUID(str(chunk_id)),
                        "rank": rank,
                        "similarity_score": score,
                    }
                )

            if retrieved_chunks_payload:
                await self.chunk_repository.bulk_create(
                    retrieved_chunks_payload,
                )

            return result

        except Exception as exc:
            latency_ms = int(
                (time.perf_counter() - started_at) * 1000
            )

            await self.trace_repository.update_metrics(
                trace.id,
                retrieval_latency_ms=latency_ms,
                total_latency_ms=latency_ms,
            )

            await self.trace_repository.update_status(
                trace.id,
                status=RetrievalTraceStatus.FAILED,
                error_message=str(exc),
            )

            raise