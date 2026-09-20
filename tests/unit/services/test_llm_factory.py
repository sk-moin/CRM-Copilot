"""The LLM provider factory must never hand back None.

It used to fall off the end for any unrecognised `LLM_PROVIDER`, returning
None. That surfaced far from the cause: `RAGChain` called `.complete()` on
None and reported "Failed to generate a response", and once the guardrails
lifespan hook was added it took the whole API down at startup with a message
about NeMo configuration.

Three integration tests were red for exactly this reason and were misdiagnosed
as an environment problem for several rounds. Nothing in the suite started the
app or exercised the factory's fallthrough, so nothing contradicted the wrong
explanation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import app.services.llm.factory as factory
from app.services.llm.providers.mock_provider import MockProvider
from app.services.llm.providers.openrouter_provider import OpenRouterProvider


class _Settings:
    def __init__(self, provider: str) -> None:
        self.LLM_PROVIDER = provider
        self.OPENROUTER_API_KEY = "test-key"
        self.OPENROUTER_MODEL = "test-model"
        self.GROQ_API_KEY = "gsk_test_not_a_real_key"
        self.GROQ_MODEL = "openai/gpt-oss-20b"
        self.APP_URL = "http://localhost:8000"


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    """get_llm_provider is lru_cached, so each test must start clean."""

    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


def _with(provider: str):
    return patch.object(
        factory,
        "get_settings",
        return_value=_Settings(provider),
    )


def test_mock_provider_is_built() -> None:
    with _with("mock"):
        assert isinstance(factory.get_llm_provider(), MockProvider)


def test_openrouter_provider_is_built() -> None:
    with _with("openrouter"):
        assert isinstance(factory.get_llm_provider(), OpenRouterProvider)


@pytest.mark.parametrize("provider", ["", "anthropic", "openai", "cohere"])
def test_unsupported_provider_raises_instead_of_returning_none(
    provider: str,
) -> None:
    """The shape of the original defect: a name nothing implements.

    This used to parametrize over "groq", which was the real `.env` value at
    the time and implemented nothing. Groq is a supported provider now, so the
    case moved to other unimplemented names.
    """

    with _with(provider):
        with pytest.raises(ValueError) as excinfo:
            factory.get_llm_provider()

    message = str(excinfo.value)

    assert repr(provider) in message
    assert "mock" in message and "openrouter" in message


def test_the_factory_never_returns_none() -> None:
    """A regression guard phrased the way the bug actually presented."""

    for provider in ("mock", "openrouter", "groq"):
        factory.get_llm_provider.cache_clear()

        with _with(provider):
            assert factory.get_llm_provider() is not None

    factory.get_llm_provider.cache_clear()

    with _with("anthropic"):
        with pytest.raises(ValueError):
            assert factory.get_llm_provider() is not None


def test_the_provider_is_built_once_per_process() -> None:
    """A fresh OpenRouter provider per request costs ~750ms and leaks an
    httpx pool that is never closed."""

    with _with("openrouter"):
        first = factory.get_llm_provider()
        second = factory.get_llm_provider()

    assert first is second


@pytest.mark.parametrize("provider", ["OpenRouter", "  openrouter  ", "MOCK"])
def test_provider_value_is_normalised(provider: str) -> None:
    """A stray capital or trailing space must not brick startup.

    GUARDRAILS_PROVIDER was normalised in an earlier repair while this one was
    left as an exact match, so the two provider settings disagreed on whether
    case mattered.
    """

    with _with(provider):
        assert factory.get_llm_provider() is not None
