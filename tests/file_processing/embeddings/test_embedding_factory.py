"""Tests for embedding provider factory."""

import pytest

from app.file_processing.embeddings.factory import create_embedding_provider
from app.file_processing.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)


def test_create_default_provider():
    """Factory should create the default embedding provider."""
    provider = create_embedding_provider()

    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.model_name == "BAAI/bge-small-en-v1.5"


def test_create_provider_with_custom_model():
    """Factory should accept a custom model name."""
    provider = create_embedding_provider(
        provider_type="sentence-transformer",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )

    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"


def test_unknown_provider_type():
    """Unknown provider types should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown embedding provider type"):
        create_embedding_provider("invalid-provider")