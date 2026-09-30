from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from langchain_core.documents import Document

from app.evaluation.runner import EvalCase, EvaluationSuite, run_eval_case


def _case(**kwargs) -> EvalCase:
    values = {
        "name": "renewal-summary",
        "query": "What is the renewal status?",
        "tenant_id": uuid4(),
        "org_id": uuid4(),
        "conversation_id": uuid4(),
    }
    values.update(kwargs)
    return EvalCase(**values)


class _AgentService:
    def __init__(self, response: str, documents: list[Document]) -> None:
        self.response = response
        self.documents = documents
        self.calls: list[dict[str, object]] = []

    async def run(self, **context):
        self.calls.append(context)
        return {
            "response": self.response,
            "retrieved_documents": self.documents,
        }


@pytest.mark.asyncio
async def test_run_eval_case_passes_when_answer_and_retrieval_match() -> None:
    case = _case(
        expected_response_terms=("renewal", "revenue"),
        expected_document_terms=("renewal", "pipeline"),
        min_documents=2,
        score_threshold=0.75,
    )
    agent = _AgentService(
        "The renewal revenue pipeline is healthy and on track.",
        [
            Document(page_content="Renewal pipeline review for 2026"),
            Document(page_content="Revenue forecast and expansion plan"),
        ],
    )

    result = await run_eval_case(case, agent_service=agent)

    assert result.passed is True
    assert result.score == 1.0
    assert result.duration_ms >= 0
    assert result.failures == []
    assert agent.calls == [
        {
            "conversation_id": case.conversation_id,
            "tenant_id": case.tenant_id,
            "user_id": None,
            "org_id": case.org_id,
            "query": case.query,
        }
    ]


@pytest.mark.asyncio
async def test_run_eval_case_fails_when_expected_answer_and_retrieval_are_missing() -> None:
    case = _case(
        expected_response_terms=("arr", "renewal"),
        expected_document_terms=("renewal",),
        min_documents=1,
        score_threshold=0.8,
    )
    agent = _AgentService(
        "The account is stable and expanding across Europe.",
        [Document(page_content="Expansion opportunity in Europe")],
    )

    result = await run_eval_case(case, agent_service=agent)

    assert result.passed is False
    assert result.score < 0.8
    assert any("Response missing expected terms" in failure for failure in result.failures)
    assert any(
        "Retrieved documents missing expected terms" in failure
        for failure in result.failures
    )
    assert any("below threshold" in failure for failure in result.failures)


@pytest.mark.asyncio
async def test_run_eval_case_fails_when_expected_answer_claim_is_not_grounded() -> None:
    case = _case(
        expected_grounded_terms=("fully funded",),
        expected_document_terms=("onboarding",),
    )
    agent = _AgentService(
        "The onboarding program is fully funded.",
        [Document(page_content="Onboarding milestones were completed.")],
    )

    result = await run_eval_case(case, agent_service=agent)

    assert result.passed is False
    assert result.score == 0.5
    assert any("Expected grounded terms" in failure for failure in result.failures)


@pytest.mark.asyncio
async def test_run_eval_case_passes_when_expected_claim_is_in_answer_and_evidence() -> None:
    case = _case(expected_grounded_terms=("fully funded",))
    agent = _AgentService(
        "The onboarding program is fully funded.",
        [Document(page_content="The onboarding program is fully funded.")],
    )

    result = await run_eval_case(case, agent_service=agent)

    assert result.passed is True
    assert result.score == 1.0


def test_eval_case_rejects_invalid_fixture_values() -> None:
    with pytest.raises(ValueError, match="score_threshold"):
        _case(score_threshold=1.1)

    with pytest.raises(ValueError, match="query"):
        EvalCase(
            name="empty-query",
            query=" ",
            tenant_id=uuid4(),
            org_id=uuid4(),
            conversation_id=uuid4(),
        )

    with pytest.raises(ValueError, match="grounded terms"):
        _case(expected_grounded_terms="not-a-sequence")


@pytest.mark.asyncio
async def test_evaluation_suite_aggregates_results() -> None:
    cases = [
        _case(
            name="healthy-onboarding",
            query="Summarize onboarding health",
            expected_response_terms=("healthy",),
            expected_document_terms=("onboarding",),
            min_documents=1,
        ),
        _case(
            name="churn-risk",
            query="Summarize churn risk",
            expected_response_terms=("churn",),
            expected_document_terms=("risk",),
            min_documents=1,
        ),
    ]
    agent = _AgentService(
        "The onboarding program is healthy and complete.",
        [Document(page_content="Onboarding milestones completed")],
    )

    summary = await EvaluationSuite(cases, agent_service=agent).run()

    assert summary["passed"] is False
    assert len(summary["results"]) == 2
    assert summary["score"] < 1.0


def test_evaluation_suite_rejects_empty_cases() -> None:
    with pytest.raises(ValueError, match="at least one case"):
        EvaluationSuite([], agent_service=_AgentService("Answer", []))


@pytest.mark.asyncio
async def test_run_eval_case_rejects_missing_scoring_criteria_before_agent_call() -> None:
    agent = _AgentService("Unvalidated answer", [])

    with pytest.raises(ValueError, match="scoring criterion"):
        await run_eval_case(_case(), agent_service=agent)

    assert agent.calls == []


@pytest.mark.asyncio
async def test_optional_judge_contributes_score_and_evidence() -> None:
    case = _case(judge_rubric="The answer must be accurate and grounded.")
    agent = _AgentService(
        "The renewal is expected in Q4.",
        [Document(page_content="Renewal expected in Q4")],
    )
    judge = AsyncMock()
    judge.complete.return_value = SimpleNamespace(
        content=json.dumps({"score": 0.8, "reason": "Grounded in the document."})
    )

    result = await run_eval_case(
        case,
        agent_service=agent,
        judge_provider=judge,
    )

    assert result.passed is True
    assert result.score == 0.8
    assert result.evidence["judge_score"] == 0.8
    assert result.evidence["judge_reason"] == "Grounded in the document."
    judge.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_judge_requires_a_rubric() -> None:
    case = _case()
    agent = _AgentService("Answer", [])
    judge = AsyncMock()

    with pytest.raises(ValueError, match="judge_rubric"):
        await run_eval_case(case, agent_service=agent, judge_provider=judge)

    assert agent.calls == []
    judge.complete.assert_not_awaited()
