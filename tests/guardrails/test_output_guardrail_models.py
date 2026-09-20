from app.guardrails.models import (
    GuardrailAction,
    OutputGuardrailResult,
)


def test_output_guardrail_result_allows_response() -> None:
    result = OutputGuardrailResult(
        allowed=True,
        content="Here is the requested CRM information.",
        action=GuardrailAction.ALLOW,
    )

    assert result.allowed is True
    assert result.action == GuardrailAction.ALLOW
    assert result.content == "Here is the requested CRM information."
    assert result.reason is None
    assert result.violations == []


def test_output_guardrail_result_blocks_response() -> None:
    result = OutputGuardrailResult(
        allowed=False,
        content="I'm sorry, but I can't assist with that request.",
        action=GuardrailAction.BLOCK,
        reason="The generated response violated a safety policy.",
        violations=["unsafe_content"],
    )

    assert result.allowed is False
    assert result.action == GuardrailAction.BLOCK
    assert result.reason == "The generated response violated a safety policy."
    assert result.violations == ["unsafe_content"]


def test_output_guardrail_result_supports_modified_response() -> None:
    result = OutputGuardrailResult(
        allowed=True,
        content="I can help with general CRM guidance.",
        action=GuardrailAction.MODIFY,
        reason="The original response contained restricted content.",
        violations=["restricted_content"],
    )

    assert result.allowed is True
    assert result.action == GuardrailAction.MODIFY
    assert result.content == "I can help with general CRM guidance."


def test_output_guardrail_result_metadata() -> None:
    result = OutputGuardrailResult(
        allowed=True,
        content="Safe response.",
        action=GuardrailAction.ALLOW,
        metadata={
            "provider": "nemo",
            "rail": "output",
        },
    )

    assert result.metadata["provider"] == "nemo"
    assert result.metadata["rail"] == "output"