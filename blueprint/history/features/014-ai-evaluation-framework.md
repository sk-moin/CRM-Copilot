# Feature: AI Evaluation Framework

**From build-plan:** feature 014
**Build attempt:** 1
**Branch:** feature/ai-evaluation-framework
**Status:** verified

## Goal

Add a lightweight, repository-native evaluation framework that catches agent and retrieval regressions before they ship. The feature gives the team a repeatable way to run a small set of quality checks over the existing FastAPI, LangGraph, and RAG stack, with deterministic rules first and optional LLM-as-judge scoring only when the project already has a configured provider path.

## In scope

- A small eval fixture format for prompts, tenant context, and expected behavior
- A runner that executes the real agent and retrieval stack against those fixtures
- Rule-based checks for answer completeness, grounding, and retrieval quality
- Optional LLM-as-judge scoring that reuses the existing provider abstraction instead of creating a new external evaluator
- A pytest-friendly report that fails on regression and keeps the output easy to inspect in CI or local runs
- Coverage for a few representative CRM and retrieval prompts to keep the framework useful without turning it into a full benchmarking platform

## Out of scope

- A production analytics dashboard or web UI for eval results
- Model benchmarking across multiple providers or a broad cost/latency comparison matrix
- Large, permanent drift datasets or curated benchmark corpora for every prompt in the application
- An external evaluation service or cloud-hosted judge workflow
- New database tables or persisted evaluation results beyond local fixture output and pytest assertions

## Build loop

- [x] 1. Define the eval fixture and scoring contract around the current agent and retrieval interfaces
- [x] 2. Build the runner and summary output that exercises real requests and captures evidence
- [x] 3. Add a concrete retrieval-quality and agent-answer eval suite and make it part of the existing pytest flow
- [x] 4. Close audit findings F-90 through F-92

## Build steps

- [x] 1. Define a lightweight evaluation contract and fixture schema
  - Done when: a fixture record can declare a prompt, tenant and org context, expected retrieval behavior, expected answer constraints, and optional score thresholds, and the project can validate malformed fixtures before execution.

- [x] 2. Build a runner that executes the real agent and retrieval stack for each fixture
  - Done when: the runner calls the existing agent or retrieval services against each case, captures the response text, retrieval evidence, duration, and pass/fail status, and returns a readable summary to the caller.

- [x] 3. Add a small eval suite for agent answers and retrieval quality and wire it into pytest
  - Done when: focused pytest cases cover at least one retrieval-quality regression and one answer-quality regression, the suite is green under the repo Verify command, and the evaluation logic stays within the current app and test stack without introducing a new external system.

- [x] 4. Reject empty evaluations and verify deterministic grounding
  - Done when: empty suites fail explicitly; cases without any scoring criterion cannot report success; cases can declare answer claims that must appear in both the response and retrieved evidence, with a regression test proving unsupported claims fail.

## Files / areas

- `app/evaluation/`
- `app/agent/`
- `app/rag/`
- `tests/unit/evaluation/`
- `tests/integration/conftest.py` for deterministic integration-test reranking
- `tests/integration/` for the representative end-to-end cases that prove the runner remains aligned with the real app

## Data / contracts

- Evaluation fixtures are plain Python objects or JSON values, not a new database model.
- Each case includes a prompt, a tenant or org context, one or more expected result signals, and an optional jailbreak, safety, or retrieval-quality rubric.
- Grounding expectations are explicit terms that must occur in both the answer and retrieved evidence; they provide a deterministic lexical grounding signal without requiring an LLM judge.
- Rule-based scoring stays simple and explicit: pass/fail, numeric score in a fixed range, and human-readable reason text.
- LLM-as-judge scoring is optional and only used when the project already has a valid provider configuration; it should never become a required dependency for basic eval execution.
- Eval output is a summary object with result name, status, score, evidence, and failing reason when applicable.

## Testing

- `python -m pytest tests/unit/evaluation`
- `python -m pytest tests/integration/test_agent_chat.py`
- `python -m pytest tests/integration/test_chat.py::test_chat_stream_success tests/unit/rag/test_reranker_cache.py`
- Repository Verify command: `alembic upgrade head && python -m pytest`

## Notes for the AI

- Keep this feature a tight evaluation harness rather than a full experimentation platform.
- Prefer deterministic checks and grounded rules before adding a model-driven judge.
- Reuse the existing agent and retrieval services so the framework is checking the same code paths the app already runs in production.
- Keep the default mode cheap and local; do not add a new external service or heavy benchmark infra in the first build.
- The eval suite should fail loudly on regressions and leave clear evidence for the next fix.

<!-- blueprint:completion {"schemaVersion":1,"specBytes":5843,"specSha256":"6de344d6220f2853bc06ea8d289714862febf592cb52f3dd10fc1c7e423d3aeb","branch":"refs/heads/feature/ai-evaluation-framework","head":"e791b0d3fbad064b20c2d5fa60031f011e6f28cf","baseRef":"refs/heads/main","baseCommit":"10ccb12ee7d89f2c2d316775aa62b357685f7798","sourceTree":"3d44c081a89dbcd6399f8da4d0d3f0db14fd4e1e4c0b83d7950bc95d7d4306ba","absentOptional":[]} -->

## Independent review

**Status:** passed
**Target commit:** e791b0d3fbad064b20c2d5fa60031f011e6f28cf
**Base commit:** 10ccb12ee7d89f2c2d316775aa62b357685f7798
**Base ref:** refs/heads/main
**Spec hash:** 6de344d6220f2853bc06ea8d289714862febf592cb52f3dd10fc1c7e423d3aeb
**Prepared by:** copilot
**Builder model:** gpt-6-luna
**Requested reviewer:** copilot
**Requested model:** runtime default (exact model not known until reviewer starts)
**Requested execution:** automatic
**Requested at:** 2026-09-30T15:12:53.3291208+05:30
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** copilot
**Reviewer model:** unknown (runtime did not expose exact model)
**Reviewer context:** fresh session
**Actual execution:** manual
**Reviewed at:** 2026-09-30T15:16:50+05:30
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

### Commands

- `python -m pytest tests/unit/evaluation -q`: pass

### Evidence

- `tests/unit/evaluation/test_eval_runner.py` covers empty-suite rejection, missing-scoring validation, grounded-term enforcement, suite aggregation, and optional judge scoring; the focused suite completed successfully.
- `app/evaluation/runner.py` enforces the active feature's validation contract and grounded evidence checks without a reachable defect in the reviewed delta.

### Findings

- None

### Remaining risk

- None identified
