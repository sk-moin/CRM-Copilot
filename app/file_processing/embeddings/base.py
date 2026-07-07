"""Abstract base class for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import EmbeddingResult


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers.

    Implementations convert text into numerical vector representations.
    Providers may use local models, remote APIs, or other embedding backends.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate an embedding for a single text string."""
        raise NotImplementedError

    @abstractmethod
    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple text strings."""
        raise NotImplementedError