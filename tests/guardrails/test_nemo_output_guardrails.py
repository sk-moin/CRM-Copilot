import pytest

from app.guardrails.exceptions import GuardrailProviderError
from app.guardrails.models import (
    GuardrailAction,
    OutputGuardrailResult,
)
from app.guardrails.service import GuardrailService


class FakeOutputProvider:
    """
    Fake provider used to test NeMo output-guardrail
    integration at the GuardrailService level.

    This intentionally implements only the provider behavior
    required by these tests.
    """

    def __init__(self, result: OutputGuardrailResult) -> None:
        self.result = result
        self.generate_calls = 0
        self.check_output_calls = 0

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def generate(
        self,
        *,
        messages,
        **kwargs,
    ) -> str:
        self.generate_calls += 1
        return "ORIGINAL RESPONSE"

    async def check_output(
        self,
        text: str,
        user_input: str | None = None,
    ) -> OutputGuardrailResult:
        self.check_output_calls += 1
        return self.result


@pytest.mark.asyncio
async def test_nemo_output_allows_safe_response() -> None:
    provider = FakeOutputProvider(
        OutputGuardrailResult(
            allowed=True,
            content="SAFE RESPONSE",
            action=GuardrailAction.ALLOW,
        )
    )

    service = GuardrailService(
        provider=provider,
    )

    result = await service.generate(
        messages=[
            {
                "role": "user",
                "content": "Show my opportunities.",
            }
        ]
    )

    assert result == "SAFE RESPONSE"

    assert provider.generate_calls == 1
    assert provider.check_output_calls == 1


@pytest.mark.asyncio
async def test_nemo_output_returns_modified_response() -> None:
    provider = FakeOutputProvider(
        OutputGuardrailResult(
            allowed=True,
            content="REDACTED RESPONSE",
            action=GuardrailAction.MODIFY,
            reason="Sensitive data removed.",
        )
    )

    service = GuardrailService(
        provider=provider,
    )

    result = await service.generate(
        messages=[
            {
                "role": "user",
                "content": "Show the customer information.",
            }
        ]
    )

    assert result == "REDACTED RESPONSE"

    assert provider.generate_calls == 1
    assert provider.check_output_calls == 1


@pytest.mark.asyncio
async def test_nemo_output_returns_fallback_when_blocked() -> None:
    provider = FakeOutputProvider(
        OutputGuardrailResult(
            allowed=False,
            content="UNSAFE RESPONSE",
            action=GuardrailAction.BLOCK,
            reason="Unsafe content.",
        )
    )

    service = GuardrailService(
        provider=provider,
    )

    result = await service.generate(
        messages=[
            {
                "role": "user",
                "content": "Give me the information.",
            }
        ]
    )

    assert result == (
        "I'm sorry, but I can't provide that response. "
        "Please try rephrasing your request."
    )

    assert provider.generate_calls == 1
    assert provider.check_output_calls == 1
@pytest.mark.asyncio
async def test_nemo_output_provider_failure_fails_closed() -> None:
    class FailingOutputProvider(FakeOutputProvider):
        async def check_output(
            self,
            text: str,
            user_input: str | None = None,
        ) -> OutputGuardrailResult:
            self.check_output_calls += 1
            raise RuntimeError("NeMo unavailable")

    provider = FailingOutputProvider(
        OutputGuardrailResult(
            allowed=True,
            content="UNUSED",
            action=GuardrailAction.ALLOW,
        )
    )

    service = GuardrailService(provider=provider)

    result = await service.generate(
        messages=[
            {
                "role": "user",
                "content": "Show my opportunities.",
            }
        ]
    )

    assert result == (
        "I'm sorry, but I can't provide that response. "
        "Please try rephrasing your request."
    )
    assert provider.generate_calls == 1
    assert provider.check_output_calls == 1


@pytest.mark.asyncio
async def test_output_guardrails_disabled_skip_provider_output_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.guardrails.config import (
        GuardrailsConfig,
        OutputGuardrailConfig,
    )
    import app.guardrails.config as config_module

    disabled_config = GuardrailsConfig(
        provider="nemo",
        output=OutputGuardrailConfig(enabled=False),
    )
    monkeypatch.setattr(
        config_module,
        "guardrails_config",
        disabled_config,
    )

    provider = FakeOutputProvider(
        OutputGuardrailResult(
            allowed=False,
            content="UNSAFE RESPONSE",
            action=GuardrailAction.BLOCK,
            reason="Unsafe content.",
        )
    )

    service = GuardrailService(provider=provider)

    result = await service.generate(
        messages=[
            {
                "role": "user",
                "content": "Show my opportunities.",
            }
        ]
    )

    assert result == "ORIGINAL RESPONSE"
    assert provider.generate_calls == 1
    assert provider.check_output_calls == 0


@pytest.mark.asyncio
async def test_nemo_output_provider_failure_can_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.guardrails.config import (
        GuardrailsConfig,
        OutputGuardrailConfig,
    )
    import app.guardrails.config as config_module

    monkeypatch.setattr(
        config_module,
        "guardrails_config",
        GuardrailsConfig(
            provider="nemo",
            output=OutputGuardrailConfig(
                enabled=True,
                fail_closed_on_error=False,
            ),
        ),
    )

    class FailingOutputProvider(FakeOutputProvider):
        async def check_output(
            self,
            text: str,
            user_input: str | None = None,
        ) -> OutputGuardrailResult:
            self.check_output_calls += 1
            raise RuntimeError("NeMo unavailable")

    provider = FailingOutputProvider(
        OutputGuardrailResult(
            allowed=True,
            content="UNUSED",
            action=GuardrailAction.ALLOW,
        )
    )

    service = GuardrailService(provider=provider)

    with pytest.raises(GuardrailProviderError) as exc_info:
        await service.generate(
            messages=[
                {
                    "role": "user",
                    "content": "Show my opportunities.",
                }
            ]
        )

    assert "NeMo output guardrail failed" in str(exc_info.value)
    assert provider.check_output_calls == 1
