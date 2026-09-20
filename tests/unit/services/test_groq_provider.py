"""GroqProvider and the model-resolution path it exposed.

Adding a provider surfaced a latent defect: the guardrails layer re-derived the
model name from `LLM_PROVIDER` with an if-chain that fell through to
"mock-model" for anything it had not been taught about. Switching to Groq
therefore sent a nonexistent model to a live API, the judge call 404'd, and
every response failed closed to the refusal message.

These tests never call the network.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

import app.services.llm.factory as factory
from app.services.llm.providers.groq_provider import (
    GROQ_BASE_URL,
    MAX_STOP_SEQUENCES,
    GroqProvider,
    _sampling,
)
from app.services.llm.providers.mock_provider import MockProvider
from app.services.llm.providers.openrouter_provider import OpenRouterProvider


class _Settings:
    LLM_PROVIDER = "groq"
    GROQ_API_KEY = "gsk_test_not_a_real_key"
    GROQ_MODEL = "openai/gpt-oss-20b"
    OPENROUTER_API_KEY = "test"
    OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
    OPENAI_MODEL = "gpt-4o"
    APP_URL = "http://localhost:8000"


@pytest.fixture
def settings() -> _Settings:
    return _Settings()


# --------------------------------------------------------------------------- #
# Client construction
# --------------------------------------------------------------------------- #


def test_the_client_targets_groq(settings):
    provider = GroqProvider(settings)

    assert str(provider._client.base_url).rstrip("/") == GROQ_BASE_URL


def test_the_provider_reports_its_own_model(settings):
    assert GroqProvider(settings).default_model == "openai/gpt-oss-20b"


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #


def test_unset_sampling_options_are_omitted():
    """An explicit None is not the same as omitting the key downstream."""

    assert _sampling(None, None, None) == {}


def test_zero_temperature_is_forwarded():
    """0.0 is falsy; the guardrail judge relies on it being sent."""

    assert _sampling(0.0, None, None) == {"temperature": 0.0}


def test_stop_sequences_are_truncated_to_the_api_limit():
    """Groq rejects a request carrying more than four stop sequences.

    NeMo passes the task's stop tokens and knows nothing of that limit, so
    truncating here is what keeps the judge call from 400ing.
    """

    options = _sampling(None, None, ["a", "b", "c", "d", "e", "f"])

    assert options["stop"] == ["a", "b", "c", "d"]
    assert len(options["stop"]) == MAX_STOP_SEQUENCES


def test_an_empty_stop_list_is_omitted():
    assert "stop" not in _sampling(None, None, [])


# --------------------------------------------------------------------------- #
# Model resolution
# --------------------------------------------------------------------------- #


def test_every_provider_answers_with_its_own_model(settings):
    """The guardrails layer asks the provider rather than mapping names."""

    assert GroqProvider(settings).default_model == settings.GROQ_MODEL
    assert OpenRouterProvider(settings).default_model == settings.OPENROUTER_MODEL
    assert MockProvider(settings).default_model == "mock-model"


def test_the_guardrail_judge_uses_the_active_provider_model(settings):
    """The defect that made every Groq response fail closed.

    A provider the guardrails layer has not been taught about must not quietly
    resolve to some other provider's model.
    """

    from app.guardrails.providers.nemo_provider import NemoGuardrailProvider

    provider = NemoGuardrailProvider(llm_provider=GroqProvider(settings))

    resolved = provider._get_model_name()

    assert resolved == "openai/gpt-oss-20b"
    assert resolved != "mock-model"


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def test_the_factory_builds_groq(settings):
    factory.get_llm_provider.cache_clear()

    with patch.object(factory, "get_settings", return_value=settings):
        assert isinstance(factory.get_llm_provider(), GroqProvider)

    factory.get_llm_provider.cache_clear()


def test_groq_is_a_supported_provider():
    assert "groq" in factory.SUPPORTED_PROVIDERS


@pytest.mark.parametrize("value", ["GROQ", "  groq  ", "Groq"])
def test_the_provider_name_is_normalised(value, settings):
    settings.LLM_PROVIDER = value

    factory.get_llm_provider.cache_clear()

    with patch.object(factory, "get_settings", return_value=settings):
        assert isinstance(factory.get_llm_provider(), GroqProvider)

    factory.get_llm_provider.cache_clear()


# --------------------------------------------------------------------------- #
# Response handling, without the network
# --------------------------------------------------------------------------- #


class _Choice:
    def __init__(self, content: str | None, finish_reason: str | None = "stop"):
        self.message = type("M", (), {"content": content})()
        self.finish_reason = finish_reason


class _Response:
    def __init__(self, choices: list[Any], usage: Any = None):
        self.choices = choices
        self.usage = usage


@pytest.mark.asyncio
async def test_no_choices_raises_rather_than_returning_none(settings):
    provider = GroqProvider(settings)

    async def _create(**kwargs):
        return _Response(choices=[])

    with patch.object(provider._client.chat.completions, "create", _create):
        with pytest.raises(RuntimeError, match="no completion choices"):
            await provider.complete(messages=[{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_empty_content_raises(settings):
    """gpt-oss models spend tokens on reasoning; a too-small max_tokens
    returns a choice whose content is None rather than text."""

    provider = GroqProvider(settings)

    async def _create(**kwargs):
        return _Response(choices=[_Choice(None, "length")])

    with patch.object(provider._client.chat.completions, "create", _create):
        with pytest.raises(RuntimeError, match="empty completion"):
            await provider.complete(messages=[{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_a_normal_completion_is_returned(settings):
    provider = GroqProvider(settings)

    async def _create(**kwargs):
        assert kwargs["model"] == "openai/gpt-oss-20b"
        return _Response(choices=[_Choice("ok")])

    with patch.object(provider._client.chat.completions, "create", _create):
        result = await provider.complete(messages=[{"role": "user", "content": "x"}])

    assert result.content == "ok"
    assert result.finish_reason == "stop"
