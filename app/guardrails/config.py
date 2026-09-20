"""
app/guardrails/config.py

Configuration for the CRM Copilot guardrail system.

Phase 2.1
---------
Input / jailbreak protection.

Phase 2.2
---------
Output validation and safety configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from app.core.config import get_settings


@dataclass(frozen=True)
class OutputGuardrailConfig:
    """
    Configuration for validating LLM-generated responses.

    This phase only defines configuration.
    Actual output validation will be implemented in Phase 2.2.2+.
    """

    # Master switch for output guardrails.
    enabled: bool = True

    # If an output rail rejects a response, the service should
    # return the configured safe fallback instead.
    block_on_violation: bool = True

    # If the provider-level output rail fails unexpectedly, fail closed
    # by returning the configured safe fallback instead of returning the
    # unvalidated model response.
    fail_closed_on_error: bool = True

    # Maximum number of characters allowed in a generated response.
    # This is a safety/configuration limit and is not the same as
    # the LLM's token limit.
    max_response_length: int = 12000

    # Response returned when the generated answer fails
    # output safety validation.
    fallback_message: str = (
        "I'm sorry, but I can't provide that response. "
        "Please try rephrasing your request."
    )

    # Whether the output guardrail should check for accidental
    # system/prompt disclosure.
    check_prompt_leakage: bool = True

    # Whether the output guardrail should check for unsafe content.
    check_unsafe_content: bool = True

    # Whether the output guardrail should reject obviously malformed
    # or empty responses.
    check_response_quality: bool = True


@dataclass(frozen=True)
class GuardrailsConfig:
    """
    Application-level guardrail configuration.
    """

    # ------------------------------------------------------------------
    # Provider
    # ------------------------------------------------------------------

    provider: str = "nemo"

    enabled: bool = True

    # ------------------------------------------------------------------
    # Input guardrails - Phase 2.1
    # ------------------------------------------------------------------

    input_enabled: bool = True

    jailbreak_detection_enabled: bool = True

    prompt_injection_detection_enabled: bool = True

    input_fallback_message: str = (
        "I'm sorry, but I can't assist with that request."
    )

    config_path: Path = Path("app/guardrails/rails")

    verbose: bool = False

    # ------------------------------------------------------------------
    # Output guardrails - Phase 2.2
    # ------------------------------------------------------------------

    output: OutputGuardrailConfig = OutputGuardrailConfig()

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------

    environment: str = "development"


def _get_bool_setting(
    name: str,
    default: bool,
) -> bool:
    """
    Read a boolean setting safely from the application settings.

    Supports both actual bool values and common string values.
    """

    value = getattr(get_settings(), name, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    return default


def _get_int_setting(
    name: str,
    default: int,
) -> int:
    """
    Read an integer setting safely from application settings.
    """

    value = getattr(get_settings(), name, default)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_str_setting(
    name: str,
    default: str,
) -> str:
    """
    Read a string setting safely from application settings.
    """

    value = getattr(get_settings(), name, default)

    if value is None:
        return default

    return str(value)


def _build_guardrails_config() -> GuardrailsConfig:
    """
    Build the runtime guardrail configuration from application settings.
    """

    output_config = OutputGuardrailConfig(
        enabled=_get_bool_setting(
            "GUARDRAIL_OUTPUT_ENABLED",
            True,
        ),
        block_on_violation=_get_bool_setting(
            "GUARDRAIL_OUTPUT_BLOCK_ON_VIOLATION",
            True,
        ),
        fail_closed_on_error=_get_bool_setting(
            "GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR",
            True,
        ),
        max_response_length=_get_int_setting(
            "GUARDRAIL_OUTPUT_MAX_RESPONSE_LENGTH",
            12000,
        ),
        fallback_message=_get_str_setting(
            "GUARDRAIL_OUTPUT_FALLBACK_MESSAGE",
            (
                "I'm sorry, but I can't provide that response. "
                "Please try rephrasing your request."
            ),
        ),
        check_prompt_leakage=_get_bool_setting(
            "GUARDRAIL_OUTPUT_CHECK_PROMPT_LEAKAGE",
            True,
        ),
        check_unsafe_content=_get_bool_setting(
            "GUARDRAIL_OUTPUT_CHECK_UNSAFE_CONTENT",
            True,
        ),
        check_response_quality=_get_bool_setting(
            "GUARDRAIL_OUTPUT_CHECK_RESPONSE_QUALITY",
            True,
        ),
    )

    return GuardrailsConfig(
        # Note the prefix split: the provider-level switches are GUARDRAILS_*
        # while the per-rail switches are GUARDRAIL_*. Reading the wrong one
        # silently returns the default, which is how the kill switch came to
        # do nothing.
        provider=_get_str_setting(
            "GUARDRAILS_PROVIDER",
            "nemo",
        ).strip().lower(),
        enabled=_get_bool_setting(
            "GUARDRAILS_ENABLED",
            True,
        ),
        config_path=Path(
            _get_str_setting(
                "GUARDRAILS_CONFIG_PATH",
                "app/guardrails/rails",
            )
        ),
        verbose=_get_bool_setting(
            "GUARDRAILS_VERBOSE",
            False,
        ),
        input_enabled=_get_bool_setting(
            "GUARDRAIL_INPUT_ENABLED",
            True,
        ),
        jailbreak_detection_enabled=_get_bool_setting(
            "GUARDRAIL_JAILBREAK_ENABLED",
            True,
        ),
        prompt_injection_detection_enabled=_get_bool_setting(
            "GUARDRAIL_PROMPT_INJECTION_ENABLED",
            True,
        ),
        input_fallback_message=_get_str_setting(
            "GUARDRAIL_INPUT_FALLBACK_MESSAGE",
            "I'm sorry, but I can't assist with that request.",
        ),
        output=output_config,
        environment=_get_str_setting(
            "ENVIRONMENT",
            "development",
        ),
    )


guardrails_config = _build_guardrails_config()