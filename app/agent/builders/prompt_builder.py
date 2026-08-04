"""
app/agent/builders/prompt_builder.py
"""

from __future__ import annotations

from langchain_core.documents import Document


class PromptBuilder:
    """
    Builds the final prompt for the CRM Copilot AI Agent.
    """

    def build(
        self,
        *,
        system_prompt: str,
        query: str,
        messages: list[dict[str, str]],
        documents: list[Document],
    ) -> str:
        """
        Build the complete prompt.
        """

        sections: list[str] = []

        # --------------------------------------------------------- #
        # System Prompt
        # --------------------------------------------------------- #

        if system_prompt:
            sections.append(system_prompt.strip())

        # --------------------------------------------------------- #
        # Conversation History
        # --------------------------------------------------------- #

        if messages:
            history_lines: list[str] = []

            for message in messages:
                role = message.get("role", "user").capitalize()
                content = message.get("content", "").strip()

                if not content:
                    continue

                history_lines.append(
                    f"{role}: {content}"
                )

            if history_lines:
                sections.append(
                    "## Conversation History\n"
                    + "\n".join(history_lines)
                )

        # --------------------------------------------------------- #
        # Retrieved Context
        # --------------------------------------------------------- #

        if documents:
            context_blocks: list[str] = []

            for index, document in enumerate(documents, start=1):
                metadata = document.metadata

                source = (
                    metadata.get("title")
                    or metadata.get("filename")
                    or f"Document {index}"
                )

                context_blocks.append(
                    f"[Source {index}] {source}\n"
                    f"{document.page_content.strip()}"
                )

            sections.append(
                "## Retrieved Context\n"
                + "\n\n".join(context_blocks)
            )

        # --------------------------------------------------------- #
        # User Query
        # --------------------------------------------------------- #

        sections.append(
            "## User Query\n"
            + query.strip()
        )

        # --------------------------------------------------------- #
        # Assistant Response
        # --------------------------------------------------------- #

        sections.append("## Assistant Response")

        # Debug
        print("=" * 80)
        print("Prompt Sections")
        print("=" * 80)

        for i, section in enumerate(sections):
            print(f"\nSECTION {i}")
            print("-" * 40)
            print(section[:500])

        print("=" * 80)

        return "\n\n".join(sections)