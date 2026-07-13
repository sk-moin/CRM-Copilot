"""
tests/rag/test_text_splitter.py
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.rag.splitters.text_splitter import (
    TextSplitter,
    create_text_splitter,
)


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def test_create_text_splitter():
    """Factory should create a TextSplitter."""

    splitter = create_text_splitter()

    assert isinstance(splitter, TextSplitter)

    assert splitter.chunk_size == 800

    assert splitter.chunk_overlap == 150


# --------------------------------------------------------------------------- #
# split_text()
# --------------------------------------------------------------------------- #


def test_split_text_short_document():
    """Short text should produce a single document."""

    splitter = create_text_splitter()

    docs = splitter.split_text(
        "CRM Copilot is an AI CRM assistant.",
        metadata={
            "source": "crm.md",
        },
    )

    assert len(docs) == 1

    doc = docs[0]

    assert isinstance(doc, Document)

    assert "CRM Copilot" in doc.page_content

    assert doc.metadata["source"] == "crm.md"

    assert "start_index" in doc.metadata


def test_split_text_large_document():
    """Large text should produce multiple chunks."""

    splitter = create_text_splitter(
        chunk_size=100,
        chunk_overlap=20,
    )

    text = " ".join(
        f"token{i}"
        for i in range(500)
    )

    docs = splitter.split_text(text)

    assert len(docs) > 1

    assert all(
        isinstance(doc, Document)
        for doc in docs
    )


def test_split_text_empty():
    """Empty text should still return one empty document."""

    splitter = create_text_splitter()

    docs = splitter.split_text("")

    assert len(docs) == 1

    assert docs[0].page_content == ""


def test_split_text_preserves_metadata():
    """Metadata should be copied to every chunk."""

    splitter = create_text_splitter(
        chunk_size=100,
        chunk_overlap=20,
    )

    text = " ".join(
        f"word{i}"
        for i in range(500)
    )

    docs = splitter.split_text(
        text,
        metadata={
            "document_id": "doc-1",
            "tenant_id": "tenant-1",
        },
    )

    for doc in docs:

        assert doc.metadata["document_id"] == "doc-1"

        assert doc.metadata["tenant_id"] == "tenant-1"

        assert "start_index" in doc.metadata


# --------------------------------------------------------------------------- #
# split_documents()
# --------------------------------------------------------------------------- #


def test_split_documents():
    """Existing LangChain Documents should be split."""

    splitter = create_text_splitter(
        chunk_size=100,
        chunk_overlap=20,
    )

    document = Document(
        page_content=" ".join(
            f"token{i}"
            for i in range(500)
        ),
        metadata={
            "source": "guide.pdf",
        },
    )

    docs = splitter.split_documents(
        [document]
    )

    assert len(docs) > 1

    assert all(
        isinstance(doc, Document)
        for doc in docs
    )


def test_split_documents_preserves_metadata():
    """Metadata should be preserved after splitting."""

    splitter = create_text_splitter(
        chunk_size=100,
        chunk_overlap=20,
    )

    document = Document(
        page_content=" ".join(
            f"token{i}"
            for i in range(500)
        ),
        metadata={
            "source": "crm.pdf",
            "document_id": "doc-123",
        },
    )

    docs = splitter.split_documents(
        [document]
    )

    for doc in docs:

        assert doc.metadata["source"] == "crm.pdf"

        assert doc.metadata["document_id"] == "doc-123"

        assert "start_index" in doc.metadata


def test_split_documents_empty():
    """Splitting an empty list should return an empty list."""

    splitter = create_text_splitter()

    docs = splitter.split_documents([])

    assert docs == []


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def test_custom_chunk_configuration():
    """Custom chunk configuration should be stored."""

    splitter = create_text_splitter(
        chunk_size=256,
        chunk_overlap=64,
    )

    assert splitter.chunk_size == 256

    assert splitter.chunk_overlap == 64