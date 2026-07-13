"""
app/rag/splitters/text_splitter.py

Text splitter for the CRM Copilot RAG pipeline.

This module wraps LangChain's RecursiveCharacterTextSplitter while exposing
a project-specific interface.

Unlike previous implementations, this splitter returns LangChain Document
objects directly so they can be passed into:

- PGVector
- Retrievers
- LCEL chains
- LangGraph workflows

without additional conversions.
"""

from __future__ import annotations

from typing import Iterable, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextSplitter:
    """Wrapper around LangChain RecursiveCharacterTextSplitter."""

    def __init__(
        self,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                "! ",
                "? ",
                " ",
                "",
            ],
            length_function=len,
            keep_separator=True,
            add_start_index=True,
        )

    def split_text(
        self,
        text: str,
        *,
        metadata: dict | None = None,
    ) -> List[Document]:
        """
        Split raw text into LangChain Documents.

        Args:
            text:
                Document text.

            metadata:
                Metadata copied to every chunk.

        Returns:
            List[Document]
        """

        if text == "":
            return [
                Document(
                    page_content="",
                    metadata=metadata or {},
                )
            ]
        return self._splitter.create_documents(
            texts=[text],
            metadatas=[metadata or {}],
        )

    def split_documents(
        self,
        documents: Iterable[Document],
    ) -> List[Document]:
        """
        Split existing LangChain documents.

        Useful when loaders already return Document objects.
        """

        return self._splitter.split_documents(
            list(documents)
        )


def create_text_splitter(
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> TextSplitter:
    """Factory for dependency injection."""

    return TextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )