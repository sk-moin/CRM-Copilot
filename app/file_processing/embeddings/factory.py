"""Factory for creating embedding providers."""

from __future__ import annotations

from .base import EmbeddingProvider
from .sentence_transformer import SentenceTransformerEmbeddingProvider

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_PROVIDER = "sentence-transformer"


def create_embedding_provider(
    provider_type: str = DEFAULT_PROVIDER,
    model_name: str | None = None,
) -> EmbeddingProvider:
    """Create an embedding provider.

    Args:
        provider_type:
            Type of embedding provider.
        model_name:
            Optional embedding model name. If omitted, the provider's
            default model is used.

    Returns:
        An initialized embedding provider.

    Raises:
        ValueError:
            If the provider type is not supported.
    """
    if provider_type == DEFAULT_PROVIDER:
        return SentenceTransformerEmbeddingProvider(
            model_name=model_name or DEFAULT_EMBEDDING_MODEL,
        )

    raise ValueError(
        f"Unknown embedding provider type '{provider_type}'. "
        f"Supported providers: {DEFAULT_PROVIDER}"
    )