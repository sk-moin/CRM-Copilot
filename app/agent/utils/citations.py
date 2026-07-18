"""
app/agent/utils/citations.py

Utilities for extracting citations from retrieved LangChain documents.
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


def build_citations(
    documents: list[Document],
) -> list[dict[str, Any]]:
    """
    Build citations from retrieved LangChain Documents.

    Parameters
    ----------
    documents:
        Retrieved documents from the RAG pipeline.

    Returns
    -------
    list[dict]
        Standardized citation metadata.
    """

    citations: list[dict[str, Any]] = []

    for document in documents:
        metadata = document.metadata

        citations.append(
            {
                "chunk_id": metadata.get("chunk_id"),
                "document_id": metadata.get("document_id"),
                "title": metadata.get("title"),
                "filename": metadata.get("filename"),
                "chunk_index": metadata.get("chunk_index"),
                "similarity_score": metadata.get("similarity_score"),
            }
        )

    return citations


def build_reference_text(
    citations: list[dict[str, Any]],
) -> str:
    """
    Build a human-readable reference section.

    Example
    -------
    Sources:
    [1] CRM Guide (crm.pdf)
    [2] Sales Handbook (sales.pdf)
    """

    if not citations:
        return ""

    lines = ["Sources:"]

    seen: set[tuple[str | None, str | None]] = set()

    index = 1

    for citation in citations:
        key = (
            citation.get("document_id"),
            citation.get("chunk_id"),
        )

        if key in seen:
            continue

        seen.add(key)

        title = citation.get("title") or "Untitled"
        filename = citation.get("filename")

        if filename:
            lines.append(
                f"[{index}] {title} ({filename})"
            )
        else:
            lines.append(
                f"[{index}] {title}"
            )

        index += 1

    return "\n".join(lines)