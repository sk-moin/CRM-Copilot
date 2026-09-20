"""
Output guardrail policy.

Phase 2.2.2
-----------
Validates LLM-generated responses before they are returned to the
application/user.

This module is intentionally provider-independent.

NeMo Guardrails remains responsible for framework-level rails, while
this policy layer provides deterministic application-level checks that
can be executed consistently regardless of the underlying provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.guardrails.config import guardrails_config


@dataclass(frozen=True)
class OutputGuardrailResult:
    """
    Result of output safety validation.
    """

    allowed: bool
    reason: str | None = None
    rule: str | None = None


# ---------------------------------------------------------------------------
# Prompt / system instruction leakage
# ---------------------------------------------------------------------------

_PROMPT_LEAKAGE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "system_prompt_disclosure",
        re.compile(
            r"\b("
            r"system prompt|system instructions|developer prompt|"
            r"developer instructions|hidden prompt|hidden instructions|"
            r"internal prompt|internal instructions"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "instruction_disclosure",
        re.compile(
            r"\b("
            r"my instructions are|my instructions say|"
            r"my system message says|"
            r"my developer message says"
            r")\b",
            re.IGNORECASE,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Secret / credential leakage
#
# These rules intentionally focus on obvious credential-like patterns.
# We do not attempt to build a complete secret scanner here.
# ---------------------------------------------------------------------------

_SECRET_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "openai_api_key",
        re.compile(
            r"\bsk-[A-Za-z0-9_-]{20,}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "github_token",
        re.compile(
            r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "aws_access_key",
        re.compile(
            r"\bAKIA[0-9A-Z]{16}\b",
        ),
    ),
    (
        "bearer_token",
        re.compile(
            r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "private_key",
        re.compile(
            r"-----BEGIN\s+(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.IGNORECASE,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Unsafe-content indicators
#
# This is deliberately conservative. Phase 2.2.2 is not intended to be
# a complete content moderation model.
# ---------------------------------------------------------------------------

_UNSAFE_CONTENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "malware_instruction",
        re.compile(
            r"\b("
            r"write|create|generate|provide|give"
            r")\b"
            r".{0,80}\b("
            r"ransomware|malware|keylogger|credential stealer"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "credential_theft_instruction",
        re.compile(
            r"\b("
            r"steal|exfiltrate|harvest|capture"
            r")\b"
            r".{0,80}\b("
            r"passwords?|credentials?|api keys?|tokens?"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def _normalize_output(response: str) -> str:
    """
    Normalize generated output before validation.
    """

    response = response.replace("\x00", " ")
    response = re.sub(r"\s+", " ", response)

    return response.strip()


def _validate_response_quality(
    response: str,
) -> OutputGuardrailResult | None:
    """
    Validate basic response quality.
    """

    if not response.strip():
        return OutputGuardrailResult(
            allowed=False,
            reason="The generated response was empty.",
            rule="empty_response",
        )

    return None


def _validate_prompt_leakage(
    response: str,
) -> OutputGuardrailResult | None:
    """
    Detect obvious system/developer prompt disclosure.
    """

    if not guardrails_config.output.check_prompt_leakage:
        return None

    for rule_name, pattern in _PROMPT_LEAKAGE_RULES:
        if pattern.search(response):
            return OutputGuardrailResult(
                allowed=False,
                reason=(
                    "The generated response appears to disclose "
                    "protected assistant instructions."
                ),
                rule=rule_name,
            )

    return None


def _validate_secrets(
    response: str,
) -> OutputGuardrailResult | None:
    """
    Detect obvious credential or secret leakage.
    """

    for rule_name, pattern in _SECRET_RULES:
        if pattern.search(response):
            return OutputGuardrailResult(
                allowed=False,
                reason=(
                    "The generated response appears to contain "
                    "sensitive credentials or secrets."
                ),
                rule=rule_name,
            )

    return None


def _validate_unsafe_content(
    response: str,
) -> OutputGuardrailResult | None:
    """
    Detect a small set of high-confidence unsafe output patterns.

    This is not intended to replace a dedicated moderation model.
    """

    if not guardrails_config.output.check_unsafe_content:
        return None

    for rule_name, pattern in _UNSAFE_CONTENT_RULES:
        if pattern.search(response):
            return OutputGuardrailResult(
                allowed=False,
                reason=(
                    "The generated response contains content that "
                    "violates the application's safety policy."
                ),
                rule=rule_name,
            )

    return None


def validate_output(
    response: str,
) -> OutputGuardrailResult:
    """
    Validate an LLM-generated response.

    Validation order:

    1. Type validation
    2. Response length
    3. Basic response quality
    4. Prompt leakage
    5. Secret leakage
    6. Unsafe-content indicators

    Returns
    -------
    OutputGuardrailResult
        allowed=True when the response is safe to return.
        allowed=False when a configured output policy is violated.
    """

    if not isinstance(response, str):
        return OutputGuardrailResult(
            allowed=False,
            reason="The generated response must be a string.",
            rule="invalid_output_type",
        )

    normalized = _normalize_output(response)

    config = guardrails_config.output

    if not config.enabled:
        return OutputGuardrailResult(
            allowed=True,
        )

    if len(normalized) > config.max_response_length:
        return OutputGuardrailResult(
            allowed=False,
            reason=(
                "The generated response exceeds the maximum "
                "allowed response length."
            ),
            rule="response_too_long",
        )

    if config.check_response_quality:
        result = _validate_response_quality(normalized)

        if result is not None:
            return result

    result = _validate_prompt_leakage(normalized)

    if result is not None:
        return result

    result = _validate_secrets(normalized)

    if result is not None:
        return result

    result = _validate_unsafe_content(normalized)

    if result is not None:
        return result

    return OutputGuardrailResult(
        allowed=True,
    )