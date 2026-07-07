"""Embedding models used by the file processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EmbeddingResult:
    """Result of an embedding operation.

    Attributes
    ----------
    embedding:
        The generated embedding vector.
    model_name:
        Name of the embedding model used.
    dimensions:
        Size of the embedding vector.
    """

    embedding: list[float]
    model_name: str
    dimensions: int