"""SentenceTransformer embedding provider implementation.

This module provides an EmbeddingProvider implementation using the
sentence-transformers library. It supports local CPU-based embedding
generation without external API calls.
"""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from .base import EmbeddingProvider
from .models import EmbeddingResult

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers models."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        """Initialize the embedding provider."""
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazily load the SentenceTransformer model."""
        if self._model is None:
            logger.info(
                "Loading SentenceTransformer model: %s",
                self.model_name,
            )
            self._model = SentenceTransformer(
                self.model_name,
                device="cpu",
            )
            logger.info("SentenceTransformer model loaded successfully.")

        return self._model

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate an embedding for a single text string."""
        if not text.strip():
            dimensions = self.model.get_sentence_embedding_dimension()

            return EmbeddingResult(
                embedding=[0.0] * dimensions,
                model_name=self.model_name,
                dimensions=dimensions,
            )

        embedding = (
            self.model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            .tolist()
        )

        return EmbeddingResult(
            embedding=embedding,
            model_name=self.model_name,
            dimensions=len(embedding),
        )

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple text strings."""
        if not texts:
            return []

        dimensions = self.model.get_sentence_embedding_dimension()

        non_empty_indices: list[int] = []
        non_empty_texts: list[str] = []

        for index, text in enumerate(texts):
            if text.strip():
                non_empty_indices.append(index)
                non_empty_texts.append(text)

        encoded_vectors: list[list[float]] = []

        if non_empty_texts:
            encoded_vectors = (
                self.model.encode(
                    non_empty_texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
                .tolist()
            )

        results: list[EmbeddingResult] = [
            EmbeddingResult(
                embedding=[0.0] * dimensions,
                model_name=self.model_name,
                dimensions=dimensions,
            )
            for _ in texts
        ]

        for index, embedding in zip(non_empty_indices, encoded_vectors):
            results[index] = EmbeddingResult(
                embedding=embedding,
                model_name=self.model_name,
                dimensions=len(embedding),
            )

        return results