"""
app/rag/embeddings/embedding_provider.py

Embedding provider abstraction for the CRM Copilot RAG pipeline.

This module wraps LangChain embedding models while exposing a
stable interface to the rest of the application.

Supported providers
-------------------
- OpenAI
- OpenRouter (OpenAI-compatible)
- Azure OpenAI (future)
- HuggingFace
"""

from __future__ import annotations

from typing import Sequence

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings
from app.rag.exceptions import EmbeddingError
from app.rag.embeddings.mock_embedding_provider import MockEmbeddingProvider
settings = get_settings()


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
            return await self._embeddings.aembed_documents(
                list(texts)
            )
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

    Supported values

    - openai
    - huggingface
    """

    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        return EmbeddingProvider(
            embeddings,
        )

    if provider == "huggingface":
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={
                "device": "cpu",
            },
            encode_kwargs={
                "normalize_embeddings": True,
            },
        )

        return EmbeddingProvider(
            embeddings,
        )

    if provider == "mock":
        return EmbeddingProvider(
            MockEmbeddingProvider()
        )

    raise EmbeddingError(
        f"Unsupported embedding provider: {provider}"
    )