"""
Input guardrail policy.

Phase 2.1
---------
Detect high-confidence prompt injection and jailbreak attempts before
the request reaches the LLM / NeMo Guardrails provider.

This module intentionally uses conservative matching. We do NOT block
generic words such as "system", "instructions", "API", or "password"
because those can legitimately appear in CRM conversations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InputGuardrailResult:
    """
    Result of input safety validation.
    """

    allowed: bool
    reason: str | None = None
    rule: str | None = None


# ---------------------------------------------------------------------------
# High-confidence prompt injection / jailbreak patterns
# ---------------------------------------------------------------------------

_INPUT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_previous_instructions",
        re.compile(
            r"\bignore\b.{0,80}\b(previous|prior|above|earlier)\b"
            r".{0,80}\b(instructions?|rules?|prompts?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "ignore_system_instructions",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b"
            r".{0,100}\b(system|developer)\b"
            r".{0,100}\b(instructions?|prompt|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "reveal_system_prompt",
        re.compile(
            r"\b("
            r"reveal|show|display|print|output|expose|give|tell"
            r")\b"
            r".{0,80}\b("
            r"system prompt|system instructions|hidden prompt|"
            r"hidden instructions|developer prompt|developer instructions"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "reveal_hidden_instructions",
        re.compile(
            r"\b("
            r"reveal|show|print|display|output|expose"
            r")\b"
            r".{0,80}\b("
            r"hidden instructions|secret instructions|internal instructions|"
            r"internal prompt|hidden prompt"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "bypass_guardrails",
        re.compile(
            r"\b("
            r"bypass|disable|remove|circumvent|evade|override"
            r")\b"
            r".{0,80}\b("
            r"guardrails?|safety|safety rules|content filters?|restrictions?"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "jailbreak_mode",
        re.compile(
            r"\b("
            r"jailbreak|dan mode|developer mode|god mode|unrestricted mode|"
            r"uncensored mode|no restrictions|without restrictions"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "role_override",
        re.compile(
            r"\b("
            r"act as|pretend to be|roleplay as|you are now|"
            r"from now on you are"
            r")\b"
            r".{0,100}\b("
            r"unrestricted|uncensored|evil|jailbroken|"
            r"unfiltered|different ai|another assistant"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "extract_secrets",
        re.compile(
            r"\b("
            r"reveal|show|print|display|give|output|extract"
            r")\b"
            r".{0,100}\b("
            r"api key|secret key|access token|authentication token|"
            r"credentials?|passwords?|private keys?|environment variables?"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_extraction",
        re.compile(
            r"\b("
            r"what are your instructions|"
            r"what is your system prompt|"
            r"what were you instructed to do|"
            r"show me your prompt|"
            r"give me your prompt"
            r")\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def _normalize_input(message: str) -> str:
    """
    Normalize user input before applying rules.

    We intentionally keep this lightweight. We don't aggressively strip
    characters because doing so can create false positives in legitimate
    CRM text.
    """

    message = message.replace("\x00", " ")
    message = re.sub(r"\s+", " ", message)
    return message.strip()


_JAILBREAK_RULES: frozenset[str] = frozenset(
    {
        "bypass_guardrails",
        "jailbreak_mode",
        "role_override",
    }
)
"""Rules that target the assistant's safety behaviour or persona.

Everything else in `_INPUT_RULES` targets the instructions or secrets
themselves and is therefore prompt injection. The split exists so
GUARDRAIL_JAILBREAK_ENABLED and GUARDRAIL_PROMPT_INJECTION_ENABLED each
control something real.
"""


def validate_input(message: str) -> InputGuardrailResult:
    """
    Validate a user message against Phase 2.1 input safety rules.

    Parameters
    ----------
    message:
        Raw user message.

    Returns
    -------
    InputGuardrailResult
        allowed=True when the message can continue.
        allowed=False when a high-confidence injection/jailbreak pattern
        is detected.
    """

    if not isinstance(message, str):
        return InputGuardrailResult(
            allowed=False,
            reason="Input must be a string.",
            rule="invalid_input_type",
        )

    normalized = _normalize_input(message)

    if not normalized:
        return InputGuardrailResult(
            allowed=False,
            reason="Input cannot be empty.",
            rule="empty_input",
        )

    # Imported here so tests can substitute the module-level singleton, and
    # to keep the policy module importable without the app config.
    from app.guardrails.config import guardrails_config

    # Type and emptiness are validity checks, not safety policy, so they run
    # above this point regardless. Only the pattern rules are switchable.
    if not guardrails_config.input_enabled:
        return InputGuardrailResult(allowed=True)

    for rule_name, pattern in _INPUT_RULES:
        if rule_name in _JAILBREAK_RULES:
            if not guardrails_config.jailbreak_detection_enabled:
                continue
        elif not guardrails_config.prompt_injection_detection_enabled:
            continue

        if pattern.search(normalized):
            return InputGuardrailResult(
                allowed=False,
                reason=(
                    "The request was blocked because it appears to "
                    "contain an attempt to bypass or extract protected "
                    "assistant instructions."
                ),
                rule=rule_name,
            )

    return InputGuardrailResult(
        allowed=True,
    )