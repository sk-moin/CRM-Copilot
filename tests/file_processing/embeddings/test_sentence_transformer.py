"""Tests for SentenceTransformerEmbeddingProvider."""

from unittest.mock import MagicMock, patch

import pytest

from app.file_processing.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)


@pytest.fixture
def provider():
    """Create embedding provider."""
    return SentenceTransformerEmbeddingProvider(
        model_name="BAAI/bge-small-en-v1.5"
    )


def test_model_is_lazy_loaded(provider):
    """Model should not be loaded until first use."""
    assert provider._model is None


@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
def test_model_loaded_once(mock_sentence_transformer, provider):
    """Model should only be loaded a single time."""
    mock_model = MagicMock()
    mock_sentence_transformer.return_value = mock_model

    first = provider.model
    second = provider.model

    assert first is second
    mock_sentence_transformer.assert_called_once_with(
        "BAAI/bge-small-en-v1.5",
        device="cpu",
    )


@pytest.mark.asyncio
@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
async def test_embed_text(mock_sentence_transformer, provider):
    """Generate embedding for one text."""
    mock_model = MagicMock()
    mock_model.encode.return_value.tolist.return_value = [0.1] * 384

    mock_sentence_transformer.return_value = mock_model

    result = await provider.embed_text("Hello world")

    assert result.model_name == "BAAI/bge-small-en-v1.5"
    assert result.dimensions == 384
    assert len(result.embedding) == 384


@pytest.mark.asyncio
@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
async def test_embed_empty_text(mock_sentence_transformer, provider):
    """Empty text should return a zero vector."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384

    mock_sentence_transformer.return_value = mock_model

    result = await provider.embed_text("")

    assert result.dimensions == 384
    assert len(result.embedding) == 384
    assert all(value == 0.0 for value in result.embedding)


@pytest.mark.asyncio
@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
async def test_embed_multiple_texts(mock_sentence_transformer, provider):
    """Batch embedding should preserve ordering."""
    mock_model = MagicMock()

    mock_model.encode.return_value.tolist.return_value = [
        [0.1] * 384,
        [0.2] * 384,
    ]
    mock_model.get_sentence_embedding_dimension.return_value = 384

    mock_sentence_transformer.return_value = mock_model

    results = await provider.embed_texts(
        [
            "First",
            "Second",
        ]
    )

    assert len(results) == 2

    assert results[0].dimensions == 384
    assert results[1].dimensions == 384

    assert results[0].embedding[0] == 0.1
    assert results[1].embedding[0] == 0.2


@pytest.mark.asyncio
@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
async def test_embed_texts_empty_list(mock_sentence_transformer, provider):
    """Empty input should return an empty list."""
    results = await provider.embed_texts([])

    assert results == []


@pytest.mark.asyncio
@patch("app.file_processing.embeddings.sentence_transformer.SentenceTransformer")
async def test_embed_texts_with_empty_strings(
    mock_sentence_transformer,
    provider,
):
    """Mixed empty/non-empty inputs should be handled correctly."""
    mock_model = MagicMock()

    mock_model.encode.return_value.tolist.return_value = [
        [0.5] * 384,
    ]
    mock_model.get_sentence_embedding_dimension.return_value = 384

    mock_sentence_transformer.return_value = mock_model

    results = await provider.embed_texts(
        [
            "",
            "Hello",
            "",
        ]
    )

    assert len(results) == 3

    assert all(v == 0.0 for v in results[0].embedding)
    assert results[1].embedding[0] == 0.5
    assert all(v == 0.0 for v in results[2].embedding)