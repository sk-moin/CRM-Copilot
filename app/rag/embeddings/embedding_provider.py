"""
app/rag/embeddings/embedding_provider.py

Embedding provider abstraction for the CRM Copilot RAG pipeline.
"""

from __future__ import annotations

from typing import Sequence

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings
from app.rag.embeddings.mock_embedding_provider import (
    MockEmbeddingProvider,
)
from app.rag.exceptions import EmbeddingError


class EmbeddingProvider:
    """Wrapper around LangChain embedding models."""

    def __init__(
        self,
        embeddings: Embeddings,
    ) -> None:
        self._embeddings = embeddings

    @property
    def client(self) -> Embeddings:
        """Return the underlying LangChain embedding client."""
        return self._embeddings

    async def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate embeddings for multiple documents."""

        try:
            return await self._embeddings.aembed_documents(list(texts))
        except Exception as exc:
            raise EmbeddingError(
                "Failed to generate document embeddings."
            ) from exc

    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Generate an embedding for a query."""

        try:
            return await self._embeddings.aembed_query(text)
        except Exception as exc:
            raise EmbeddingError(
                "Failed to generate query embedding."
            ) from exc


def create_embedding_provider() -> EmbeddingProvider:
    """
    Create the configured embedding provider.

    Supported providers:
    - huggingface
    - openai
    - mock
    """

    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "huggingface":
        # Imported here, not at module scope. langchain_huggingface pulls in
        # sentence-transformers and torch, roughly 2 GB, and importing this
        # module used to drag all of it into every process that touched the
        # app -- including a test run pinned to the mock provider, and any CI
        # job that only runs tests.
        from langchain_huggingface import HuggingFaceEmbeddings

        return EmbeddingProvider(
            HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={
                    "device": "cpu",
                },
                encode_kwargs={
                    "normalize_embeddings": True,
                },
            )
        )

    if provider == "openai":
        return EmbeddingProvider(
            OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        )

    if provider == "mock":
        return EmbeddingProvider(
            MockEmbeddingProvider()
        )

    raise EmbeddingError(
        f"Unsupported embedding provider: {provider}"
    )