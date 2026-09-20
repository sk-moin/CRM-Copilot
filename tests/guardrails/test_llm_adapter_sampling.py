"""The guardrail adapter must forward NeMo's sampling controls to the provider.

NeMo calls the judge as `generate_async(prompt, stop=stop, **llm_params)`, where
`llm_params` carries the task temperature and token cap. The adapter used to
accept `stop` and swallow `**kwargs` without passing either on, so the judge ran
at the provider's default temperature with no stop sequence.

That is not cosmetic. `is_content_safe` reads only the first two words of the
answer and treats anything it does not recognize as a policy violation, so a
judge that replies "The response is acceptable." instead of "No." gets a good
answer blocked — and `ChatService` persists that refusal in place of the real
answer.
"""

from __future__ import annotations

import pytest

from app.guardrails.providers.llm_adapter import GuardrailLLMAdapter
from app.services.llm.models import CompletionResult, TokenUsage


class RecordingProvider:
    """Captures exactly what the adapter passed down."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)

        return CompletionResult(
            content="no",
            usage=TokenUsage.empty(),
            finish_reason="stop",
        )


@pytest.fixture
def provider() -> RecordingProvider:
    return RecordingProvider()


@pytest.fixture
def adapter(provider: RecordingProvider) -> GuardrailLLMAdapter:
    return GuardrailLLMAdapter(provider=provider, model="recording-model")


@pytest.mark.asyncio
async def test_stop_and_llm_params_reach_the_provider(
    adapter: GuardrailLLMAdapter,
    provider: RecordingProvider,
) -> None:
    await adapter.generate_async(
        "Should the assistant response be blocked?",
        stop=["\n"],
        temperature=0.0,
        max_tokens=1024,
    )

    call = provider.calls[0]

    assert call["stop"] == ["\n"]
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_unset_options_are_omitted_entirely(
    adapter: GuardrailLLMAdapter,
    provider: RecordingProvider,
) -> None:
    """An explicit None is not the same as omitting the key downstream."""

    await adapter.generate_async("Anything at all.")

    call = provider.calls[0]

    assert "stop" not in call
    assert "temperature" not in call
    assert "max_tokens" not in call


@pytest.mark.asyncio
async def test_unknown_options_are_dropped_not_forwarded(
    adapter: GuardrailLLMAdapter,
    provider: RecordingProvider,
) -> None:
    """A NeMo upgrade that adds a new llm_param must not break the call."""

    await adapter.generate_async(
        "Anything at all.",
        temperature=0.0,
        some_future_nemo_option="surprise",
    )

    call = provider.calls[0]

    assert call["temperature"] == 0.0
    assert "some_future_nemo_option" not in call
