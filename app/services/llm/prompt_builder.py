"""Prompt builder for LLM providers.

This module is responsible for converting conversation history and context into
provider-ready chat messages. It is intentionally provider-agnostic and contains
no database or networking logic.

Message order:

1. System prompt
2. Retrieved context (future RAG support)
3. Conversation history
4. Current user message

This design allows future Prompt Management (Spec 005) and Context Builder /
RAG (Specs 006+) without changing ChatService.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class PromptBuilder:
    """Build provider-ready prompts from chat history."""

    @staticmethod
    def build(
        *,
        system_prompt: str,
        history: Sequence[Any],
        user_message: str,
        context: Sequence[str] | None = None,
    ) -> list[dict[str, str]]:
        """Build a provider-ready message list.

        Args:
            system_prompt:
                The system instruction supplied by configuration or Prompt
                Management.

            history:
                Ordered conversation history. Each item must expose
                ``role`` and ``content`` attributes (or equivalent).

            user_message:
                Latest user message.

            context:
                Retrieved knowledge snippets (currently optional).
                Future RAG implementations will populate this.

        Returns:
            List of provider-ready messages.

        Example:
            [
                {"role": "system", "content": "..."},
                {"role": "system", "content": "...context..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "..."},
            ]
        """

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        ]

        # ------------------------------------------------------------------
        # Retrieved Context (future RAG)
        # ------------------------------------------------------------------

        if context:
            context_text = "\n\n".join(
                item.strip()
                for item in context
                if item and item.strip()
            )

            if context_text:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Use the following retrieved context when it is "
                            "relevant to answering the user's question.\n\n"
                            f"{context_text}"
                        ),
                    }
                )

        # ------------------------------------------------------------------
        # Conversation History
        # ------------------------------------------------------------------

        for message in history:
            role = PromptBuilder._extract_role(message)
            content = PromptBuilder._extract_content(message)

            if not content:
                continue

            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        # ------------------------------------------------------------------
        # Current User Message
        # ------------------------------------------------------------------

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    @staticmethod
    def _extract_role(message: Any) -> str:
        """Extract the role from a history message."""

        role = getattr(message, "role", None)

        if role is None:
            role = message.get("role") if isinstance(message, dict) else "user"

        if hasattr(role, "value"):
            return str(role.value)

        return str(role)

    @staticmethod
    def _extract_content(message: Any) -> str:
        """Extract content from a history message."""

        content = getattr(message, "content", None)

        if content is None and isinstance(message, dict):
            content = message.get("content", "")

        return str(content or "")

    @staticmethod
    def build_system_prompt(
        *,
        assistant_name: str = "CRM Copilot",
        additional_instructions: str | None = None,
    ) -> str:
        """Build the default system prompt.

        This helper exists so Prompt Management (Spec 005) can later replace
        this implementation without affecting ChatService.
        """

        prompt = (
            f"You are {assistant_name}, an AI assistant for a CRM platform.\n\n"
            "Provide clear, accurate, and concise answers.\n"
            "Use the supplied conversation history and retrieved context when "
            "available.\n"
            "If you do not know the answer, say so rather than inventing "
            "information."
        )

        if additional_instructions:
            prompt += f"\n\n{additional_instructions.strip()}"

        return prompt