"""
app/agent/builders/prompt_builder.py

Prompt builder for the CRM Copilot AI Agent.

Responsibilities
----------------
- Build the final prompt sent to the LLM
- Combine system instructions, conversation history,
  retrieved context, and the current user query

This class does NOT:
- Retrieve documents
- Call the LLM
- Execute LangGraph nodes
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.agent.prompts.system_prompt import get_system_prompt


class PromptBuilder:
    """
    Builds the final prompt for the CRM Copilot AI Agent.
    """

    def build(
        self,
        *,
        query: str,
        messages: list[dict[str, str]],
        documents: list[Document],
    ) -> str:
        """
        Build the complete prompt.

        Parameters
        ----------
        query:
            Current user query.

        messages:
            Conversation history.

        documents:
            Retrieved LangChain documents.

        Returns
        -------
        str
            Complete prompt ready for the LLM.
        """

        sections: list[str] = []

        # --------------------------------------------------------- #
        # System Prompt
        # --------------------------------------------------------- #

        sections.append(get_system_prompt())

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
                    (
                        f"[Source {index}] {source}\n"
                        f"{document.page_content.strip()}"
                    )
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
        # Assistant
        # --------------------------------------------------------- #

        sections.append("## Assistant Response")

        return "\n\n".join(sections)