import inspect

from app.guardrails.providers.base import GuardrailProvider


def test_guardrail_provider_defines_check_output() -> None:
    assert hasattr(GuardrailProvider, "check_output")

    method = getattr(GuardrailProvider, "check_output")

    assert inspect.iscoroutinefunction(method)
    assert getattr(method, "__isabstractmethod__", False) is True