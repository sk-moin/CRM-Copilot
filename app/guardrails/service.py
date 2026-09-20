"""
Guardrail service.

Responsibilities
----------------
- Validate user input before it reaches the LLM.
- Delegate allowed requests to the configured guardrail provider.
- Provide a provider-independent interface to the API/chat layer.

Phase 2.1
---------
Adds prompt-injection / jailbreak detection at the service boundary.

Phase 6.1
---------
Exposes input validation without triggering LLM generation so the real
ChatService can reject unsafe input before persisting it or invoking the
AI agent.
"""

from __future__ import annotations

import logging
from typing import Any

from app.guardrails.exceptions import (
    GuardrailInputBlockedError,
    GuardrailProviderError,
)
from app.guardrails.policies.input import validate_input
from app.guardrails.providers.base import GuardrailProvider
from app.guardrails.policies.output import validate_output

logger = logging.getLogger(__name__)

class GuardrailService:
    """
    High-level guardrail service.

    The service owns policy enforcement.

    The provider owns the actual NeMo Guardrails execution.
    """

    def __init__(
        self,
        *,
        provider: GuardrailProvider,
    ) -> None:
        self.provider = provider

    async def initialize(self) -> None:
        """
        Initialize the underlying guardrail provider.
        """

        await self.provider.initialize()

    async def shutdown(self) -> None:
        """
        Shut down the underlying guardrail provider.
        """

        await self.provider.shutdown()

    @property
    def initialized(self) -> bool:
        """
        Return provider initialization state when available.
        """

        return bool(
            getattr(
                self.provider,
                "initialized",
                False,
            )
        )

    @property
    def input_fallback_message(self) -> str:
        """The user-facing refusal for a blocked input.

        Exposed here so callers use the injected service rather than reading
        the module-level `guardrails_config`, which a dependency override
        cannot control.
        """

        from app.guardrails.config import guardrails_config

        return guardrails_config.input_fallback_message

    def validate_input(self, message: str) -> None:
        """
        Validate a user message before it reaches the AI pipeline.

        This is the application-boundary input guardrail used by
        ChatService and other callers that need validation without
        triggering an LLM generation.

        Raises
        ------
        GuardrailInputBlockedError
            When the input violates an input safety policy.
        """
        validation = validate_input(message)

        if not validation.allowed:
            raise GuardrailInputBlockedError(
                message=validation.reason
                or "The request was blocked by the input safety policy.",
                rule=validation.rule,
            )

    async def validate_output(
        self,
        response_text: str,
        user_input: str | None = None,
    ) -> str:
        """
        Validate an already-generated assistant response.

        This method performs output guardrail checks without generating
        another LLM response.

        Flow:

            generated response
                ↓
            static output policy
                ↓
            NeMo output rails
                ↓
            safe / modified / fallback response
        """

        output_config = self._get_output_config()

        # Output guardrails disabled.
        if not output_config.enabled:
            return response_text

        # ---------------------------------------------------------------
        # Phase 2.2.2 — Deterministic output validation
        # ---------------------------------------------------------------

        output_validation = validate_output(response_text)

        if not output_validation.allowed:
            if output_config.block_on_violation:
                logger.warning(
                    "guardrail.output.blocked",
                    extra={
                        "stage": "static_policy",
                        "rule": output_validation.rule,
                    },
                )
                return output_config.fallback_message

        # ---------------------------------------------------------------
        # Phase 2.2.3.3 — NeMo output rails
        # ---------------------------------------------------------------

        try:
            nemo_result = await self.provider.check_output(
                response_text,
                user_input=user_input,
            )

        except GuardrailProviderError:
            if output_config.fail_closed_on_error:
                logger.warning(
                    "guardrail.output.fail_closed",
                    extra={"stage": "provider", "reason": "provider_error"},
                    exc_info=True,
                )
                return output_config.fallback_message

            raise

        except Exception as exc:
            if output_config.fail_closed_on_error:
                logger.warning(
                    "guardrail.output.fail_closed",
                    extra={"stage": "provider", "reason": "unexpected_error"},
                    exc_info=True,
                )
                return output_config.fallback_message

            raise GuardrailProviderError(
                f"NeMo output guardrail failed: {exc}"
            ) from exc

        if nemo_result.allowed:
            return nemo_result.content

        if output_config.block_on_violation:
            logger.warning(
                "guardrail.output.blocked",
                extra={"stage": "provider_rail"},
            )
            return output_config.fallback_message

        return nemo_result.content

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """
        Run a guarded generation request.

        Flow:

            input validation
                ↓
            guardrail provider / LLM generation
                ↓
            static output validation
                ↓
            NeMo output rails
                ↓
            safe response
        """

        user_message = self._extract_latest_user_message(
            messages
        )

        self.validate_input(user_message)

        try:
            response = await self.provider.generate(
                messages=messages,
                **kwargs,
            )

        except GuardrailInputBlockedError:
            raise

        except Exception as exc:
            raise GuardrailProviderError(
                f"Guardrail provider failed: {exc}"
            ) from exc

        response_text = self._extract_response_text(
            response
        )

        # Delegate to validate_output rather than repeating its branches.
        # This half used to be a second copy of the same policy, which is how
        # it ended up without any logging when validate_output gained it.
        return await self.validate_output(
            response_text,
            user_input=user_message,
        )


        

    @staticmethod
    def _extract_latest_user_message(
        messages: list[dict[str, Any]],
    ) -> str:
        """
        Extract the latest user message.

        System and assistant messages are intentionally ignored.

        This prevents policy checks from accidentally treating the
        system prompt or previous assistant output as the user's input.
        """

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            role = message.get("role")

            if role != "user":
                continue

            content = message.get("content")

            if isinstance(content, str):
                return content

            # Basic support for structured content.
            if isinstance(content, list):
                text_parts: list[str] = []

                for item in content:
                    if not isinstance(item, dict):
                        continue

                    if item.get("type") == "text":
                        text = item.get("text")

                        if isinstance(text, str):
                            text_parts.append(text)

                return " ".join(text_parts)

        raise GuardrailInputBlockedError(
            message="No user message was provided.",
            rule="missing_user_message",
        )

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """
        Normalize provider responses to a string.

        The current NemoGuardrailProvider already returns str, so this
        method mainly gives us a defensive boundary for future providers.
        """

        if isinstance(response, str):
            return response

        if response is None:
            raise GuardrailProviderError(
                "Guardrail provider returned an empty response."
            )

        # Support a simple object exposing content.
        content = getattr(response, "content", None)

        if isinstance(content, str):
            return content

        return str(response)

    @staticmethod
    def _get_output_config():
        """
        Return the configured output guardrail settings.
        """

        from app.guardrails.config import guardrails_config

        return guardrails_config.output