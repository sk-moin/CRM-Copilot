"""
Dependency injection helpers for Guardrails.
"""

from functools import lru_cache

from app.services.llm.factory import get_llm_provider
from app.guardrails.config import guardrails_config
from app.guardrails.exceptions import GuardrailConfigurationError
from app.guardrails.providers.nemo_provider import (
    NemoGuardrailProvider,
)
from app.guardrails.service import GuardrailService


@lru_cache
def get_guardrail_service() -> GuardrailService:
    """
    Return the singleton GuardrailService.

    The guardrail provider reuses the application's existing
    LLMProvider rather than creating a second LLM client.
    """

    if guardrails_config.provider != "nemo":
        # Honour the setting instead of silently running NeMo anyway. There is
        # one provider today; a typo used to be ignored, which meant an
        # operator could believe they had switched guardrails off or over.
        raise GuardrailConfigurationError(
            f"Unknown guardrail provider {guardrails_config.provider!r}. "
            "Supported providers: 'nemo'. To turn rails off, set "
            "GUARDRAILS_ENABLED=false for the provider rails and "
            "GUARDRAIL_INPUT_ENABLED=false for the input pattern rules; "
            "they are separate switches."
        )

    llm_provider = get_llm_provider()

    provider = NemoGuardrailProvider(
        llm_provider=llm_provider,
    )

    return GuardrailService(provider=provider)