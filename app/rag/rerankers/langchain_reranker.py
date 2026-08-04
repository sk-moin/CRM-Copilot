from __future__ import annotations

from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.documents import Document

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