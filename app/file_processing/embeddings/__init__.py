"""Embedding layer exports.

This module re-exports the public symbols of the embeddings package
for convenient import.
"""

from .base import EmbeddingProvider
from .models import EmbeddingResult
from .sentence_transformer import SentenceTransformerEmbeddingProvider
from .factory import create_embedding_provider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "SentenceTransformerEmbeddingProvider",
    "create_embedding_provider",
]