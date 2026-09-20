"""
NVIDIA NeMo Guardrails provider.

This provider owns the NeMo Guardrails runtime while delegating actual
LLM inference to CRM Copilot's existing LLMProvider abstraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import RailStatus, RailType

from app.guardrails.config import guardrails_config
from app.guardrails.exceptions import (
    GuardrailConfigurationError,
    GuardrailProviderError,
)
from app.guardrails.models import (
    GuardrailAction,
    OutputGuardrailResult,
)
from app.guardrails.providers.base import GuardrailProvider
from app.guardrails.providers.llm_adapter import GuardrailLLMAdapter
from app.services.llm.base import LLMProvider


class NemoGuardrailProvider(GuardrailProvider):
    """NVIDIA NeMo Guardrails implementation."""

    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        self._llm_provider = llm_provider
        self._rails: LLMRails | None = None
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Return whether NeMo Guardrails is initialized."""
        return self._initialized

    @property
    def rails(self) -> LLMRails | None:
        """Return the underlying NeMo LLMRails instance."""
        return self._rails

    async def initialize(self) -> None:
        """
        Initialize NVIDIA NeMo Guardrails.

        LLMRails is created once during application startup and reused
        across requests.
        """

        if self._initialized:
            return

        if not guardrails_config.enabled:
            self._initialized = True
            self._rails = None
            return

        try:
            config_path = Path(
                guardrails_config.config_path
            ).resolve()

            if not config_path.exists():
                raise GuardrailConfigurationError(
                    "Guardrails configuration path does not exist: "
                    f"{config_path}"
                )

            if not config_path.is_dir():
                raise GuardrailConfigurationError(
                    "Guardrails configuration path must be a directory: "
                    f"{config_path}"
                )

            config_file = config_path / "config.yml"

            if not config_file.exists():
                raise GuardrailConfigurationError(
                    f"NeMo config.yml not found: {config_file}"
                )

            model_name = self._get_model_name()

            llm_adapter = GuardrailLLMAdapter(
                self._llm_provider,
                model=model_name,
            )

            config = RailsConfig.from_path(
                str(config_path)
            )

            self._rails = LLMRails(
                config,
                llm=llm_adapter,
                verbose=guardrails_config.verbose,
            )

            self._initialized = True

        except GuardrailConfigurationError:
            raise

        except Exception as exc:
            self._rails = None
            self._initialized = False

            raise GuardrailConfigurationError(
                "Failed to initialize NVIDIA NeMo Guardrails."
            ) from exc

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """
        Execute a request through NeMo Guardrails.
        """

        if not self._initialized:
            raise GuardrailProviderError(
                "NeMo Guardrails provider has not been initialized."
            )

        # Guardrails disabled: use the existing LLM directly.
        if self._rails is None:
            result = await self._llm_provider.complete(
                messages=messages,
                model=self._get_model_name(),
            )

            if isinstance(result, str):
                return result

            content = getattr(result, "content", None)

            if not isinstance(content, str):
                raise GuardrailProviderError(
                    "LLM provider returned an invalid completion."
                )

            return content

        try:
            options = kwargs.get("options")

            response = await self._rails.generate_async(
                messages=messages,
                options=options,
            )

            return self._extract_content(response)

        except GuardrailProviderError:
            raise

        except Exception as exc:
            raise GuardrailProviderError(
                "NeMo Guardrails generation failed."
            ) from exc

    async def shutdown(self) -> None:
        """
        Release NeMo Guardrails resources.
        """

        self._rails = None
        self._initialized = False

    async def health_check(self) -> dict[str, Any]:
        """Return provider health information."""

        return {
            "initialized": self._initialized,
            "enabled": guardrails_config.enabled,
            "provider": "nemo",
            "config_path": str(
                guardrails_config.config_path
            ),
            "rails_loaded": self._rails is not None,
            "llm_provider": getattr(
                self._llm_provider.settings,
                "LLM_PROVIDER",
                None,
            ),
        }

    def _get_model_name(self) -> str:
        """Return the model the application's LLM provider uses.

        This used to re-derive the model from LLM_PROVIDER with an if-chain
        that fell through to "mock-model" for anything it had not been taught
        about. Adding a provider therefore sent a nonexistent model name to a
        live API, the judge call 404'd, and every response failed closed to the
        refusal message. Ask the provider instead.
        """

        return self._llm_provider.default_model

    @staticmethod
    def _extract_content(response: Any) -> str:
        """
        Normalize NeMo's generation response into plain text.
        """

        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            content = response.get("content")

            if isinstance(content, str):
                return content

            response_content = response.get("response")

            if isinstance(response_content, str):
                return response_content

            if isinstance(response_content, list):
                for item in reversed(response_content):
                    if isinstance(item, dict):
                        content = item.get("content")

                        if isinstance(content, str):
                            return content

        content = getattr(response, "content", None)

        if isinstance(content, str):
            return content

        raise GuardrailProviderError(
            "NeMo Guardrails returned a response without text content."
        )

    async def check_output(
        self,
        text: str,
        user_input: str | None = None,
    ) -> OutputGuardrailResult:
        """
        Evaluate an already-generated LLM response using
        NVIDIA NeMo Guardrails output rails.

        No new LLM generation is performed.
        """

        if not isinstance(text, str):
            raise GuardrailProviderError(
                "Output guardrail input must be a string."
            )

        if not self._initialized:
            raise GuardrailProviderError(
                "NeMo Guardrails provider has not been initialized."
            )

        if not text.strip():
            return OutputGuardrailResult(
                allowed=True,
                content=text,
                action=GuardrailAction.ALLOW,
                metadata={
                    "provider": "nemo",
                    "guardrails_enabled": True,
                },
            )

        # Guardrails disabled.
        if self._rails is None:
            return OutputGuardrailResult(
                allowed=True,
                content=text,
                action=GuardrailAction.ALLOW,
                metadata={
                    "provider": "nemo",
                    "guardrails_enabled": False,
                },
            )

        try:
            # The self-check prompt renders {{ user_input }}; without the
            # user turn it is blank and the rule about answering the user's
            # request cannot be evaluated.
            messages: list[dict[str, str]] = []

            if user_input:
                messages.append({"role": "user", "content": user_input})

            messages.append({"role": "assistant", "content": text})

            # Pin the rail type. NeMo picks rails from message roles, so
            # including the user turn (needed for {{ user_input }}) would
            # otherwise fire the input rails here too — double judge cost, and
            # an input rail could block an output check.
            result = await self._rails.check_async(
                messages=messages,
                rail_types=[RailType.OUTPUT],
            )

            status = result.status
            guarded_content = getattr(
                result,
                "content",
                None,
            )

            if not isinstance(guarded_content, str):
                guarded_content = text

            # ---------------------------------------------------------
            # PASSED
            # ---------------------------------------------------------

            if status == RailStatus.PASSED:
                return OutputGuardrailResult(
                    allowed=True,
                    content=guarded_content,
                    action=GuardrailAction.ALLOW,
                    metadata={
                        "provider": "nemo",
                        "guardrails_enabled": True,
                        "status": "passed",
                    },
                )

            # ---------------------------------------------------------
            # MODIFIED
            # ---------------------------------------------------------

            if status == RailStatus.MODIFIED:
                return OutputGuardrailResult(
                    allowed=True,
                    content=guarded_content,
                    action=GuardrailAction.MODIFY,
                    reason="Output was modified by NeMo Guardrails.",
                    metadata={
                        "provider": "nemo",
                        "guardrails_enabled": True,
                        "status": "modified",
                        "rail": getattr(
                            result,
                            "rail",
                            None,
                        ),
                    },
                )

            # ---------------------------------------------------------
            # BLOCKED
            # ---------------------------------------------------------

            if status == RailStatus.BLOCKED:
                return OutputGuardrailResult(
                    allowed=False,
                    content=guarded_content,
                    action=GuardrailAction.BLOCK,
                    reason="Output was blocked by NeMo Guardrails.",
                    violations=[
                        rail
                        for rail in [
                            getattr(result, "rail", None)
                        ]
                        if isinstance(rail, str)
                    ],
                    metadata={
                        "provider": "nemo",
                        "guardrails_enabled": True,
                        "status": "blocked",
                    },
                )

            raise GuardrailProviderError(
                f"Unknown NeMo output rail status: {status}"
            )

        except GuardrailProviderError:
            raise

        except Exception as exc:
            raise GuardrailProviderError(
                "NeMo output guardrail evaluation failed."
            ) from exc