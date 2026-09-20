"""Construction of the configured LLM provider.

This lives in its own module rather than in `app.api.dependencies` because
`app.guardrails.dependencies` needs it, and importing it from the API layer
created a cycle: the guardrails module imported the API module, which imported
the guardrails module back. That cycle was survivable only through a
carefully-placed mid-file import, which meant a routine tidy-up would have
broken startup.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers.groq_provider import GroqProvider
from app.services.llm.providers.mock_provider import MockProvider
from app.services.llm.providers.openrouter_provider import OpenRouterProvider

SUPPORTED_PROVIDERS = ("groq", "mock", "openrouter")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Cached: settings are a process singleton, so the key is constant. Without
    the cache every chat and RAG request built a fresh provider, and for
    OpenRouter that means a fresh AsyncOpenAI and a fresh httpx.AsyncClient
    that is never closed — measured at roughly 750 ms of dead latency per
    request, no connection reuse, and a growing set of leaked pools.

    Raises:
        ValueError: when `LLM_PROVIDER` names a provider that does not exist.
            This used to return None instead, which surfaced much later as
            "NoneType has no attribute complete" from inside the RAG chain, or
            as a guardrail initialisation failure that took the whole API down
            at startup with an unrelated-looking message.
    """

    settings = get_settings()

    # Normalised for the same reason GUARDRAILS_PROVIDER is: a stray capital or
    # trailing space should not brick startup.
    provider = (settings.LLM_PROVIDER or "").strip().lower()

    if provider == "groq":
        return GroqProvider(settings)

    if provider == "mock":
        return MockProvider(settings)

    if provider == "openrouter":
        return OpenRouterProvider(settings)

    raise ValueError(
        f"Unsupported LLM_PROVIDER {settings.LLM_PROVIDER!r}. "
        f"Supported values: {', '.join(repr(p) for p in SUPPORTED_PROVIDERS)}."
    )
