"""Route tests for /api/v1/rag/query.

This route had no test at all, which is how it came to be unable to return a
successful response: the `sources` it built were missing two fields `RAGSource`
requires, so any query that retrieved a chunk raised a ValidationError inside
the handler, was swallowed by the generic 500 handler, and surfaced as
"Failed to generate a response."

Adding guardrails to this route made that worse, not better — replacing
`detail=str(exc)` with a fixed message muted the only clue. So these tests
exercise the success path, not just the guarded paths.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.api.dependencies import get_rag_service
from app.guardrails.dependencies import get_guardrail_service
from app.guardrails.exceptions import GuardrailInputBlockedError
from app.main import app


class StubDocument:
    def __init__(self, content: str, metadata: dict) -> None:
        self.page_content = content
        self.metadata = metadata


class StubRAGResponse:
    def __init__(self, answer: str, documents, scores) -> None:
        self.answer = answer
        self.documents = documents
        self.similarity_scores = scores


class StubRAGService:
    def __init__(self, answer: str = "Acme has 3 open opportunities.") -> None:
        self.answer = answer

    async def ask(self, **kwargs) -> StubRAGResponse:
        document = StubDocument(
            content="Acme Corp renewal notes.",
            metadata={
                "chunk_id": uuid4(),
                "document_id": uuid4(),
                "chunk_index": 0,
                "title": "Acme Notes",
                "filename": "acme.pdf",
            },
        )

        return StubRAGResponse(self.answer, [document], [0.91])


class PassThroughGuardrails:
    input_fallback_message = "I'm sorry, but I can't assist with that request."

    def validate_input(self, message: str) -> None:
        return None

    async def validate_output(self, response_text, user_input=None) -> str:
        return response_text


class BlockingInputGuardrails(PassThroughGuardrails):
    def validate_input(self, message: str) -> None:
        raise GuardrailInputBlockedError(
            message="Blocked by input guardrail.",
            rule="test_rule",
        )


class BlockingOutputGuardrails(PassThroughGuardrails):
    REPLACEMENT = "I'm sorry, but I can't provide that response."

    async def validate_output(self, response_text, user_input=None) -> str:
        return self.REPLACEMENT


def _override(guardrails, rag_service=None):
    app.dependency_overrides[get_guardrail_service] = lambda: guardrails
    app.dependency_overrides[get_rag_service] = lambda: (
        rag_service or StubRAGService()
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_guardrail_service, None)
    app.dependency_overrides.pop(get_rag_service, None)


PAYLOAD = {"query": "How many open opportunities does Acme have?", "top_k": 3}


@pytest.mark.asyncio
async def test_successful_query_returns_sources(authed_client):
    """The path that was returning 500 for every retrieval."""

    _override(PassThroughGuardrails())

    response = await authed_client.post("api/v1/rag/query", json=PAYLOAD)

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["answer"] == "Acme has 3 open opportunities."
    assert body["retrieved_chunks"] == 1

    source = body["sources"][0]

    assert source["content"] == "Acme Corp renewal notes."
    assert source["similarity_score"] == pytest.approx(0.91)


@pytest.mark.asyncio
async def test_blocked_input_returns_the_refusal_not_an_answer(authed_client):
    _override(BlockingInputGuardrails())

    response = await authed_client.post("api/v1/rag/query", json=PAYLOAD)

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["answer"] == PassThroughGuardrails.input_fallback_message
    assert body["retrieved_chunks"] == 0
    assert body["sources"] == []

    # Internal guardrail detail must not reach the client.
    assert "test_rule" not in response.text
    assert "GuardrailInputBlockedError" not in response.text


@pytest.mark.asyncio
async def test_output_rail_replaces_the_answer(authed_client):
    """The output rail must reach the client, which requires a working
    success path — this fails if the response cannot be built."""

    _override(BlockingOutputGuardrails())

    response = await authed_client.post("api/v1/rag/query", json=PAYLOAD)

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["answer"] == BlockingOutputGuardrails.REPLACEMENT
    assert "Acme has 3 open opportunities." not in response.text


@pytest.mark.asyncio
async def test_internal_errors_do_not_leak_exception_text(authed_client):
    class ExplodingRAGService:
        async def ask(self, **kwargs):
            raise RuntimeError("connection string postgres://secret@host/db")

    _override(PassThroughGuardrails(), ExplodingRAGService())

    response = await authed_client.post("api/v1/rag/query", json=PAYLOAD)

    assert response.status_code == 500
    assert "secret" not in response.text
    assert response.json()["detail"] == "Failed to generate a response."


@pytest.mark.asyncio
async def test_query_requires_authentication(client):
    response = await client.post("api/v1/rag/query", json=PAYLOAD)

    assert response.status_code == 401
