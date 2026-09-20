from app.guardrails.config import (
    guardrails_config,
)


def test_guardrails_config_has_output_configuration():
    output = guardrails_config.output

    assert output.enabled is True
    assert output.block_on_violation is True
    assert output.fail_closed_on_error is True
    assert output.max_response_length == 12000

    assert output.check_prompt_leakage is True
    assert output.check_unsafe_content is True
    assert output.check_response_quality is True


def test_guardrails_output_has_fallback_message():
    output = guardrails_config.output

    assert output.fallback_message
    assert len(output.fallback_message) > 0


def test_guardrails_provider_defaults_to_nemo():
    """The default only.

    This deliberately does not prove the setting is read — it cannot, because
    it asserts the same value the default produces. The switch itself is
    covered by tests/unit/guardrails/test_settings_are_functional.py, which
    rebuilds the config from an overridden setting.
    """

    assert guardrails_config.provider == "nemo"