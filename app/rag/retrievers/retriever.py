"""
app/rag/retrievers/retriever.py

Tenant-aware retrieval layer for the CRM Copilot RAG pipeline.

Responsibilities
----------------
- Retrieve semantically similar documents
- Apply similarity score threshold
- Return LangChain Documents
- Return similarity scores for retrieval observability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from langchain_core.documents import Document

from app.rag.exceptions import RetrievalError
from app.rag.vectorstores.pgvector_store import PGVectorStore


# --------------------------------------------------------------------------- #
# Retrieval Result
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class RetrievalResult:
    """
    Result returned by the retriever.
    """

    documents: list[Document]
    similarity_scores: list[float]

    @property
    def retrieved_chunks(self):
        return len(self.documents)
   


# --------------------------------------------------------------------------- #
# Retriever
# --------------------------------------------------------------------------- #


class Retriever:
    """
    Tenant-aware semantic retriever.
    """

    def __init__(
        self,
        vector_store: PGVectorStore,
    ) -> None:
        self.vector_store = vector_store

    # ------------------------------------------------------------------ #
    # Retrieve
    # ------------------------------------------------------------------ #

    async def retrieve(
        self,
        *,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        document_id: UUID | None = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents.
        """

        if not query.strip():
            raise RetrievalError(
                "Query cannot be empty."
            )

        results = await self.vector_store.similarity_search_with_scores(
            query=query,
            k=top_k,
            document_id=document_id,
        )

        results = [
            (doc, score)
            for doc, score in results
            if score >= score_threshold
        ]

        documents = [
            doc
            for doc, _ in results
        ]

        scores = [
            score
            for _, score in results
        ]

        return RetrievalResult(
            documents=documents,
            similarity_scores=scores,
        )

    # ------------------------------------------------------------------ #
    # Documents Only
    # ------------------------------------------------------------------ #

    async def retrieve_documents(
        self,
        *,
        query: str,
        top_k: int = 5,
        document_id: UUID | None = None,
    ) -> list[Document]:
        """
        Retrieve only documents.
        """

        result = await self.retrieve(
            query=query,
            top_k=top_k,
            document_id=document_id,
        )

        return result.documents

    # ------------------------------------------------------------------ #
    # Documents + Scores
    # ------------------------------------------------------------------ #

    async def retrieve_with_scores(
        self,
        *,
        query: str,
        top_k: int = 5,
        document_id: UUID | None = None,
    ) -> list[tuple[Document, float]]:
        """
        Retrieve documents together with similarity scores.
        """

        if not query.strip():
            raise RetrievalError(
                "Query cannot be empty."
            )

        return await self.vector_store.search(
            query=query,
            top_k=top_k,
            score_threshold=0.0,
            document_id=document_id,
        )