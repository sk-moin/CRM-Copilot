from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document

@dataclass(slots=True)
class RerankedDocument:
    document: Document
    rerank_score: float


class LangChainReranker:
    """
    LangChain wrapper around HuggingFace CrossEncoder.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        top_n: int = 5,
    ) -> None:

        # Imported here, not at module scope. These pull in
        # sentence-transformers and torch, roughly 2 GB, and importing this
        # module used to drag all of it into every process that touched the
        # RAG package -- including test runs that never rerank anything.
        # Construction already loads the model, so this defers nothing that
        # was not already deferred.
        from langchain_classic.retrievers.document_compressors import (
            CrossEncoderReranker,
        )
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder

        model = HuggingFaceCrossEncoder(
            model_name=model_name,
        )

        self._reranker = CrossEncoderReranker(
            model=model,
            top_n=top_n,
        )

    def rerank(
        self,
        query: str,
        documents: list[Document],
    ) -> list[RerankedDocument]:

        return self._reranker.compress_documents(
            documents=documents,
            query=query,
        )