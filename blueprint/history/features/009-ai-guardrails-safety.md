# Feature: AI Guardrails & Safety

**From build-plan:** feature 009
**Build attempt:** 1
**Status:** verified
**Branch:** feature/ai-guardrails-safety

## Goal

Make the already-built guardrail layer actually govern the chat response path.
`app/guardrails/` ships a working NeMo provider, input and output policies, five
dialog rails, and 72 passing tests, but two of its contracts never reach a user:
`GuardrailService.validate_output` has no production caller, and a blocked input
surfaces as a raw exception name instead of the configured refusal message.

This feature closes both gaps at the `chat_service` boundary and leaves the
guardrail package itself unchanged.

## In scope

- Deliver `GUARDRAIL_INPUT_FALLBACK_MESSAGE` to the client when input rails block
  a message, instead of a `GuardrailInputBlockedError` SSE error frame.
- Call `GuardrailService.validate_output` on the generated response before it is
  streamed to the client.
- Persist the validated response text, so the stored assistant message equals
  what the user was shown.
- Tests covering pass-through, blocked, provider-error, and disabled paths, plus
  one integration test through the real SSE endpoint.
- Commit the existing untracked `app/guardrails/`, `tests/guardrails/`,
  `tests/unit/guardrails/`, `app/api/routes/guardrails.py`, and
  `app/api/schemas/guardrails.py` work as part of this feature branch.
- **Folded-in repair (step 4).** A pre-existing uncommitted defect in
  `packages/database/repositories/document_chunk_repository.py` breaks the
  retrieve node, so no agent response is produced and the output rails from
  step 2 cannot be verified end to end. Added to this branch by user decision
  rather than a separate `/fix` record, because it blocks this feature's
  verification and `/fix` would overwrite this spec.

## Out of scope

- **PII leakage detection.** Named on the build-plan line for 009 but absent from
  the code. Descoped by decision; V2 item 028 (PII Redaction) already covers it.
  The build-plan line for 009 should be amended to match.
- **Hallucinated CRM fact / groundedness checking.** Also named on the 009 line,
  also absent, also descoped by the same decision. It is its own design problem
  (comparing answers against retrieved chunks) and needs its own build-plan item.
- Moving rails onto the LangGraph graph. Chat is the only agent entrypoint today;
  revisit if a second one appears.
- New config keys. Every setting this feature needs already exists in
  `app/core/config.py` lines 64-85.
- Recording guardrail decisions in `message_metadata` or the audit log. No
  current requirement.
- Rate limiting, approval workflows, evaluation — features 010, 012, 014.

## Build loop

`workflow.stepReview` is `feature`: implement all steps, then present one review
packet. `workflow.checkpointCommits` is `disabled`: no per-step commits.
`/complete` creates the single feature commit.

## Build steps

- [x] **1. Blocked input returns the configured refusal.**
  `ChatService.stream_response` calls `validate_input` at line 123, before the
  user message is persisted. Catch `GuardrailInputBlockedError` there and yield
  the configured fallback message as a normal assistant token followed by a
  terminal chunk, rather than letting it reach the generic `except Exception`
  in `chat.py:61`. Preserve the existing behavior that a blocked exchange is
  **not** persisted — the current guard already runs before
  `message_repo.create`.
  *Done when:* a unit test on `ChatService` asserts that a message rejected by
  input rails yields exactly `GUARDRAIL_INPUT_FALLBACK_MESSAGE` as the token,
  never the exception class name or internal detail, and that no Message row is
  created. `python -m pytest tests/` passes.

- [x] **2. Output rails govern the delivered response.**
  In `ChatService.stream_response`, replace the direct use of
  `agent_state["response"]` with the result of
  `await self._guardrail_service.validate_output(full_response)`. Use that same
  validated value for both the `StreamChunk(token=...)` yield and the
  `content=` argument to `message_repo.create`, so the persisted message and the
  delivered text cannot diverge. `validate_output` already handles its own
  errors and always returns a string, so no new exception handling is needed
  here.
  *Done when:* four cases are covered, each at the layer that actually owns the
  behavior. At `ChatService`: a clean response passes through unchanged, and a
  response the output policy rejects is replaced in both the stream and the
  persisted row. At `GuardrailService`, which owns both branches: a provider
  error with `GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR` true yields the fallback
  (`tests/guardrails/test_nemo_output_guardrails.py::test_nemo_output_provider_failure_fails_closed`),
  and `GUARDRAIL_OUTPUT_ENABLED` false passes the response through
  (`::test_output_guardrails_disabled_skip_provider_output_check`). Restating
  the latter two at `ChatService` against a fake would assert only that the
  fake returns what the test configured.

- [x] **3. Integration coverage through the real endpoint.**
  Add a test to `tests/integration/test_chat.py` that drives the SSE chat route
  end to end, asserting the blocked-input and blocked-output paths produce the
  configured messages as `ChatStreamToken` frames rather than `ChatStreamError`
  frames. The guardrail service is replaced by a stub, so this covers the route,
  `ChatService`, and SSE serialization — not the rails themselves. Real rail
  behavior is covered separately by step 5's
  `tests/guardrails/test_rails_polarity.py`.
  *Done when:* `python -m pytest tests/` passes with the new integration test
  included, and no existing test in `tests/guardrails/` or
  `tests/unit/guardrails/` was modified to accommodate the change.

- [x] **4. Unblock retrieval (folded-in repair).**
  In `DocumentChunkRepository.similarity_search_with_scores`, the debug log
  calls `len(result)` on the SQLAlchemy `Result` rather than the materialized
  `rows`, raising `TypeError: object of type 'ChunkedIteratorResult' has no
  len()`. Change it to `len(rows)`. In the same method, delete the dead debug
  block that queries a hardcoded `debug_doc` UUID: it runs an extra unbounded
  query on every retrieval, discards its result, and carries no `tenant_id`
  filter, which violates the project's tenant-scoping rule.
  *Done when:* the `TypeError` no longer occurs, no hardcoded UUID remains in
  the repository, and every query in the method is tenant-scoped.
  *Outcome:* all three met. The `TypeError` is gone — retrieval now proceeds
  past the repository into reranking, and `tests/adversarial/test_tenant_isolation.py`
  still passes. The originally drafted criterion also named
  `test_chat_stream_success` and `::test_chat_stream_returns_usage` passing;
  those two remain red for an unrelated environment reason recorded under
  Testing, not because of this repair.

- [x] **5. Repair F-01: inverted output rail polarity.**
  Independent review found the `self_check_output` prompt asks "Is the
  assistant response safe?" while NeMo's `is_content_safe` reads "yes" as
  *block* and "no" as *allow*, so the rail blocked every safe answer and
  delivered every unsafe one. Wiring `validate_output` in step 2 is what armed
  this previously inert defect. Reword the prompt to NeMo's convention and add
  a test that runs the real rails.
  *Done when:* a safe response passes and an unsafe one is blocked when a judge
  that reads the prompt answers it truthfully, and the test fails against the
  previous prompt.
  *Outcome:* met. `tests/guardrails/test_rails_polarity.py` — 7 passed against
  the fix, 3 failed against the reverted prompt. `tests/guardrails` +
  `tests/unit`: 173 passed, no regressions.

- [x] **6. Repair F-02: authenticate the guardrails endpoints.**
  `GET /guardrails/health` and `POST /guardrails/test` took no auth dependency
  while every other route required HTTPBearer, leaving an unmetered LLM proxy
  open to anyone who could reach the service. Add `Depends(get_current_user)`
  to both, matching the pattern in `rag.py` and `audit.py`. Authenticating
  rather than deleting keeps the endpoints available; no role helper exists in
  this project, so a role guard would mean new machinery.
  *Done when:* both routes carry a security requirement in the generated
  OpenAPI schema.
  *Outcome:* met. Both now report `[{'HTTPBearer': []}]`, matching
  `/chat/stream`. Note that any authenticated user of any tenant can still
  spend tokens through `/guardrails/test`; narrowing it to an admin role, or
  deleting it, is a follow-up decision.

- [x] **7. Repair F-03: delete the dead cross-tenant AuditLog reads.**
  Two unfiltered `select(AuditLog)` full-table reads whose results were never
  used, at `audit_repository.py:166` and `routes/audit.py:36`. Same defect
  class as the debug block removed in step 4 — fixing only the instance in
  front of me left the siblings in place.
  *Done when:* no unfiltered `AuditLog` read remains and the now-unused
  imports are gone.
  *Outcome:* met. Both statements deleted along with the `select` and
  `AuditLog` imports they were the only users of in `routes/audit.py`.
  `grep -rn "execute(select(AuditLog))"` returns nothing.

- [x] **8. Repair F-04: load the cross-encoder once per process.**
  `RetrievalService.reranker` built a new `LangChainReranker` per instance, and
  `get_retrieval_service` is uncached, so every chat request loaded its own
  copy of the model. Move construction behind an `@lru_cache` factory,
  mirroring `get_guardrail_service`, keeping the load lazy.
  *Done when:* two separately constructed services share one reranker, nothing
  is loaded until first use, and an injected reranker still wins.
  *Outcome:* met. `tests/unit/rag/test_reranker_cache.py` — 3 passed.

- [x] **9. Repair F-06 through F-16 from the second independent review.**
  The re-review closed F-01 through F-05 but raised F-13 (P1): the guardrail
  LLM adapter discarded NeMo's `stop` and `llm_params`, so the judge ran
  unpinned and a prose verdict was read as a violation, destroying the answer.
  Repair that and the remaining carried findings.
  *Done when:* every finding F-06 through F-16 is repaired with focused tests
  where the logic warrants them, and the suite is no worse than before.
  *Outcome:* met. F-13 threads `temperature`, `max_tokens` and `stop` through
  `LLMProvider` and both implementations. F-06 wires six dead settings,
  including the kill switch. F-07 emits a terminal SSE frame on refusal. F-08
  logs every block. F-09 brings `/rag/query` under the same rails and stops it
  leaking `str(exc)`. F-10 renders the user turn into the judge prompt. F-11
  reads the refusal from the injected service. F-12, F-14, F-15 and F-16 are
  hygiene. Final run: 353 passed, 3 failed, the three pre-existing RAG-path
  failures.

- [x] **10. Repair F-24 through F-29 from the fourth independent review.**
  The pass closed every outstanding finding but raised a P0 proven by
  execution: the API could not start, because `get_llm_provider()` returned
  `None` for the configured `LLM_PROVIDER=groq` and the lifespan hook added by
  this feature turned that into a boot failure. It is also the true cause of
  the three integration failures this spec had misattributed to the machine.
  *Done when:* the factory cannot return `None`, the three tests pass for the
  right reason, and the remaining findings are repaired.
  *Outcome:* met, and the suite is green for the first time at 376 passed, 0
  failed. Provider construction moved to `app/services/llm/factory.py`, which
  also breaks the API/guardrails import cycle that F-22 had only documented
  (F-29). `/guardrails/test` no longer 500s on a blocked message (F-25).
  `MockProvider.complete` now honours the interface's return type (F-28).

## Files / areas

| Path | Change |
|---|---|
| `app/services/chat_service.py` | Both wirings. The only production file this feature edits. |
| `tests/unit/services/test_chat_services.py` | Unit coverage for steps 1 and 2. |
| `tests/integration/test_chat.py` | Integration coverage for step 3. |
| `app/guardrails/**` | **Unchanged.** Already built and green; committed as-is. |
| `app/core/config.py` | **Unchanged.** All needed settings exist. |

## Data / contracts

- `GuardrailService.validate_output(response_text: str) -> str` — already
  implemented. Always returns a string; never raises when
  `GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR` is true. Returns the original text when
  allowed, `GUARDRAIL_OUTPUT_FALLBACK_MESSAGE` when blocked.
- `GuardrailService.validate_input(message: str) -> None` — already implemented.
  Raises `GuardrailInputBlockedError` on violation.
- **Delivered text equals persisted text.** `Message.content` must be the same
  string the client received. This is the one data-integrity rule the feature
  adds; the immutable message history must not record a response the user never
  saw.
- **Blocked input creates no rows.** No Message, no AuditLog. Matches the
  existing guard placement.
- SSE frame shapes (`ChatStreamToken`, `ChatStreamUsage`, `ChatStreamDone`,
  `ChatStreamError`) are unchanged. Guardrail refusals travel as
  `ChatStreamToken`, not `ChatStreamError` — a refusal is an answer, not a
  transport failure.

## Testing

`python -m pytest` with `pytest.ini` (`asyncio_mode = auto`). Requires the
Postgres test container: `docker compose up -d postgres` (localhost:5433).

**Status: suite fully green. 376 passed, 0 failed.**

| Suite | Result |
|---|---|
| unit, guardrails, agent, adversarial, repositories, database, integration | 376 passed |

**Correction to earlier versions of this section.** Three integration tests
(`test_chat_stream_success`, `test_chat_stream_returns_usage`,
`test_chat_api.py::test_chat_stream_endpoint`) were recorded here through three
review rounds as pre-existing environment failures caused by a HuggingFace
cross-encoder exhausting the machine's paging file. That diagnosis was wrong.
The fourth review pass proved the cause was F-24: `LLM_PROVIDER=groq` named a
provider that was never implemented, the factory returned `None` for it, and
`RAGChain` called `.complete()` on `None`. All three pass with a valid
provider. The paging-file error was real but was an earlier, separate symptom
of the per-request reranker construction fixed in F-04; after that repair the
true cause changed and the old explanation was carried forward without being
re-tested.

The suite now pins `LLM_PROVIDER=mock` in `tests/conftest.py`, so it never
depends on a live paid API and a red suite is never ambiguous between a code
defect and a provider outage.

Two known environment quirks, both pre-existing and unrelated to this feature:

- `python -m pytest tests/` (the `tests/` directory as a single argument) fails
  to import numpy. Passing the subdirectories explicitly works. Worth resolving
  before `/ci` declares a Verify command.
- The repository root contains `custom_jwt/`, `passlib/`, and `redis/`
  directories that shadow installed packages.

No browser test harness is configured, and no `Browser tests` command exists in
`AGENTS.md`, so this feature adds no browser coverage.

> Resolved by pinning the mock provider in `tests/conftest.py`.

## Notes for the AI

- The response is **not** token-streamed. `agent_service.run()` returns a
  complete `agent_state`, and the whole response goes out as one `StreamChunk`.
  Output validation therefore needs no buffering or partial-token strategy.
- Do not modify anything under `app/guardrails/`. It is complete for this
  feature's scope and its 72 tests are the regression net.
- Do not add config keys. Read `GUARDRAIL_OUTPUT_*` and
  `GUARDRAIL_INPUT_FALLBACK_MESSAGE` from `app/core/config.py`.
- The working tree carries 18 modified files from features 006 and 008 alongside
  the untracked guardrails work. Confirm before branching that everything the
  branch will carry belongs to 009, or land the 006/008 remainder first.
- `AGENTS.md` still lists the placeholder Next.js commands (`npm run dev`,
  `npm run build`). There is no declared Verify command for this Python project,
  so `/complete` has no automatic gate to run. Run `/ci` to declare one, or
  expect to verify with `python -m pytest tests/` by hand.

## Independent review

Five independent review passes were run against this feature by fresh isolated
reviewers (adapter `claude`, model `claude-opus-5[1m]`, context `fresh
subagent`). No `passed` receipt was produced, so no receipt is archived as
passing. The honest record:

| Pass | Target | Verdict | What it found |
|---|---|---|---|
| 1 | a9b07d8b | changes-requested | Inverted output-rail polarity (P0), unauthenticated LLM proxy (P0), 10 more |
| 2 | e9fa6610 | changes-requested | Adapter discarding NeMo's sampling params (P1), 3 more |
| 3 | 24c2b314 | approved with findings | Two endpoints that had never worked (P2), 5 more |
| 4 | 45e44acb | changes-requested | The API could not start (P0), 5 more |
| 5 | 29834a7e | changes-requested | Integration tests green against a guardrail refusal (P1), per-request LLM provider (P1), 5 more |

Every pass found a real defect. Passes 4 and 5 found defects in the repairs
made for the preceding pass, and twice corrected a diagnosis the builder had
stated confidently: first that three failing integration tests were an
environment problem, then that they were "green for the right reason".

A sixth pass was offered and the user declined it, electing to complete. The
two P1 findings from pass 5 are therefore recorded as `accepted`: repaired and
builder-verified, but not independently re-reviewed. Everything in the Findings
section below at `closed` status was verified by a later pass.

## Findings

### 9/F-01 [P0] closed - Output self-check rail polarity is inverted

**File:** app/guardrails/rails/prompts.yml:24
**Found:** 2026-09-19 by /audit independent current (scope: current; lenses: quality, security, performance, tests)
**Why it matters:** The prompt asks "Is the assistant response safe and appropriate? Answer only yes or no." NeMo's `self_check_output` parses that with `is_content_safe`, whose contract is the opposite: `"yes"` returns `[False]` (unsafe, block) and `"no"` returns `[True]` (safe, pass). Confirmed against the installed nemoguardrails 0.23.0 source. The rail therefore blocks every safe answer and delivers every unsafe one. Because the delivered value is also the persisted value (verified claim 3), the real answer is destroyed, not just hidden. Before this feature `validate_output` had no production caller, so the inverted rail was inert; wiring it up is what makes it harmful.
**Suggested fix:** Reword the prompt to NeMo's convention ("Should the bot message be blocked? Answer Yes or No."), or register an output parser that inverts the result the way `self_check_facts` does. Pair with F-05.
**Resolution:** Closed 2026-09-20 by independent re-review against checkpoint e9fa661, which verified the parser contract in the installed library rather than from our tests. Fixed 2026-09-19 in build step 5. `app/guardrails/rails/prompts.yml` now asks "Should the assistant response be blocked?" and states the rules as block conditions, matching `is_content_safe`. No code change was needed. Added `tests/guardrails/test_rails_polarity.py` (7 tests) which drives the real `RailsConfig`/`LLMRails`. Its `HonestJudge` stub reads the rendered prompt and answers truthfully rather than returning a canned verdict, so it fails when the prompt and parser disagree: 3 failed against the reverted buggy prompt, 7 passed against the fix. A first draft of the test used canned verdicts and passed against the buggy prompt — the same test theater F-05 describes — and was rewritten.

### 9/F-02 [P0] closed - Guardrails endpoints are unauthenticated and proxy the LLM

**File:** app/api/routes/guardrails.py:20
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: security)
**Why it matters:** Neither `GET /api/v1/guardrails/health` nor `POST /api/v1/guardrails/test` depends on `get_current_user`, and the app declares no global auth dependency. Both were confirmed to carry no security requirement in the generated OpenAPI schema while `/chat/stream` and `/rag/query` both require HTTPBearer. Anyone who can reach the service can post arbitrary text to `/guardrails/test` and receive a completion from the configured model: an open, unmetered LLM proxy on the project's API key, with no tenant, no rate limit and no audit trail. `/health` additionally discloses provider class, init state and config path to anonymous callers.
**Suggested fix:** Add `Depends(get_current_user)` to both routes, or drop `guardrails_router` from `app/main.py:65` if it was only a development aid. Nothing in the feature spec requires these endpoints.
**Resolution:** Closed 2026-09-20 by independent re-review, which confirmed live 401s on both routes via ASGI transport, not just the OpenAPI schema, and confirmed the anonymous root `/health` liveness probe is unaffected. Fixed 2026-09-19 in build step 6. Both routes now take `Depends(get_current_user)`, matching `rag.py` and `audit.py`. Verified in the generated OpenAPI schema: both report `[{'HTTPBearer': []}]`. Authenticating was chosen over deleting because the endpoints were not confirmed to be dev-only and no role helper exists in this project, so a role guard would have meant new machinery. Residual risk: any authenticated user of any tenant can still spend tokens through `/guardrails/test`. Narrowing it to an admin role or deleting it remains an open product decision.

### 9/F-03 [P1] closed - Dead non-tenant-scoped full-table AuditLog reads

**File:** packages/database/repositories/audit_repository.py:166
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: security)
**Why it matters:** `rows = await self.session.execute(select(AuditLog))` runs an unfiltered, unbounded read across every tenant and is then never used. The same statement exists at `app/api/routes/audit.py:36`, which additionally reaches into the private `audit_service._session`. This is the identical defect class the folded-in step 4 repair claimed to eliminate, and it violates the locked rule that every tenant-owned query filters by `tenant_id`. No data reaches the client today because the result is discarded, so this is one line away from cross-tenant disclosure rather than a live leak.
**Suggested fix:** Delete both lines. Nothing reads `rows`.
**Resolution:** Closed 2026-09-20 by independent re-review, which confirmed the four remaining `select(AuditLog)` sites are all tenant-filtered and no tenant scoping was lost elsewhere in the delta. Fixed 2026-09-19 in build step 7. Both statements deleted, along with the now-unused `select` and `AuditLog` imports in `app/api/routes/audit.py`, which also removes the private `audit_service._session` access noted in F-12. `grep -rn "execute(select(AuditLog))"` over `app/` and `packages/` returns nothing. 271 tests pass across unit, guardrails, agent, adversarial, repositories and database suites, including `tests/adversarial/test_tenant_isolation.py`.

### 9/F-04 [P1] closed - Cross-encoder reranker is constructed per request

**File:** app/rag/retrieval_service.py:58
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: performance)
**Why it matters:** A module-level reranker singleton was replaced by a lazy per-instance property, but `get_retrieval_service` is an uncached FastAPI dependency, so every chat request builds a new `RetrievalService` and therefore loads a fresh `BAAI/bge-reranker-base` cross-encoder. `LangChainReranker.__init__` has no caching. N concurrent requests load N copies of the model. This is plausibly the same resource exhaustion currently recorded as environmental in the spec's Testing section.
**Suggested fix:** Keep the lazy load but cache the instance at module scope, for example an `@lru_cache` factory mirroring `get_guardrail_service`, or have `get_retrieval_service` reuse one reranker.
**Resolution:** Closed 2026-09-20 by independent re-review, which confirmed single construction, lazy load, injection precedence, and that the classic lru_cache threading race is unreachable because the only caller is a coroutine with no await inside the factory. Fixed 2026-09-19 in build step 8. Added an `@lru_cache(maxsize=1) get_default_reranker()` factory in `app/rag/retrieval_service.py`; the property now calls it instead of constructing directly, keeping the load lazy. `tests/unit/rag/test_reranker_cache.py` (3 passed) asserts two separately constructed services share one instance, nothing loads until first use, and an injected reranker still wins. Note this did not clear the pre-existing RAG-path integration failures; reverting the change reproduces them identically, so the cross-encoder was not their sole cause.

### 9/F-05 [P1] closed - No test exercises a real guardrail

**File:** tests/guardrails/test_nemo_output_guardrails.py:11
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: tests)
**Why it matters:** Every guardrail test asserts against a fake configured to return the expected value. `NemoGuardrailProvider.check_output` is never run against a real `LLMRails`, which is precisely why F-01 passes the entire suite. The unit-level fakes are legitimate for testing the seam that this feature builds, but nothing above them closes the loop. The integration test's own description claims it drives the route "with guardrails enabled" while the guardrail service is replaced by a stub. Separately, spec step 2's `Done when` names four `ChatService` cases and only two exist at that layer.
**Suggested fix:** Add one test that builds the real `RailsConfig.from_path("app/guardrails/rails")` with a stub judge LLM and asserts a safe response passes and an unsafe one is blocked. That test fails today and is the regression net for F-01.
**Resolution:** Closed 2026-09-20 by independent re-review, which mutation-tested the test itself: it copied the rails to a scratchpad, restored the pre-fix prompt from `e9fa661^`, and re-ran the harness, getting 3 failures in the expected direction against the old prompt and 7 passes against the current one. Fixed 2026-09-19 in build step 5. `tests/guardrails/test_rails_polarity.py` drives the real `RailsConfig`/`LLMRails`. Its `HonestJudge` stub reads the rendered prompt and answers truthfully instead of returning a canned verdict, which is what makes it able to fail: a first draft using canned verdicts passed against the inverted prompt, reproducing exactly the theater this finding describes, and was rewritten. The canned-verdict cases were kept but renamed and documented as pinning NeMo's upstream convention, explicitly not guarding our wording. The two overstated claims were also corrected in the spec rather than papered over: step 3 no longer says the integration test runs "with guardrails enabled" when it stubs the service, and step 2 now names where each of its four cases is actually covered.

### 9/F-06 [P2] closed - Six guardrail settings are silently non-functional, including the kill switch

**File:** app/guardrails/config.py:213
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `_build_guardrails_config()` never reads `GUARDRAILS_ENABLED`, `GUARDRAILS_CONFIG_PATH`, `GUARDRAILS_VERBOSE`, and reads a `GUARDRAIL_PROVIDER` key that does not exist (the setting is `GUARDRAILS_PROVIDER`), so the provider always falls back to `"nemo"`. The three input flags it does read are never consulted by `policies/input.py`. With F-01 live, an operator cannot disable guardrails without a code change and redeploy. `config_path` also stays a relative path resolved against the process CWD while the setting meant to override it is ignored, so starting the server from another directory fails at lifespan.
**Suggested fix:** Wire the six settings, minding the `GUARDRAILS_`/`GUARDRAIL_` prefix split, and have `policies/input.py` honor the input flags. Deleting the dead fields is equally acceptable; shipping a switch that does nothing is not.
**Resolution:** Fixed 2026-09-20. Wired the four provider-level settings in `_build_guardrails_config` (correcting `GUARDRAIL_PROVIDER` to `GUARDRAILS_PROVIDER`, and adding `enabled`, `config_path`, `verbose`), and made `policies/input.py` honour the three input flags. Rules are split into `_JAILBREAK_RULES` and the rest so the two detection switches each control something real. Type and emptiness checks still run when `input_enabled` is false, because those are validity, not safety policy. `tests/unit/guardrails/test_settings_are_functional.py` (9 tests) rebuilds the config from overridden settings rather than asserting defaults, so it fails if a setting stops being read. Third review found a residue: `GUARDRAILS_PROVIDER` was read but never consulted, so the operator-visible symptom was unchanged. `get_guardrail_service` now validates it and raises `GuardrailConfigurationError` on an unknown value instead of silently running NeMo, so a typo can no longer look like a successful switch.

### 9/F-07 [P2] closed - Blocked input never emits a terminal SSE frame

**File:** app/services/chat_service.py:135
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The blocked path yields one `StreamChunk` carrying `finish_reason="content_filter"`, but `app/api/routes/chat.py:38` emits the token and `continue`s, so the finish reason is dropped and no `ChatStreamDone` follows (`message_id` is `None` because nothing is persisted). Spec step 1 states the token should be followed by a terminal chunk; it is not. A client that waits for `ChatStreamDone` to re-enable its composer hangs until the connection closes. This was a known limitation at implementation time, recorded because `ChatStreamDone.message_id` is a required UUID, but it was not carried into the spec text.
**Suggested fix:** Emit the done frame on `finish_reason` rather than on `message_id`, which requires making `ChatStreamDone.message_id` optional, or yield a terminal chunk the route recognizes.
**Resolution:** Fixed 2026-09-20. `ChatService` now yields a terminal `StreamChunk(is_final=True, finish_reason="content_filter")` after the refusal token, and `app/api/routes/chat.py` emits `ChatStreamDone` on `is_final` when there is no message id. `ChatStreamDone.message_id` and `conversation_id` are now optional, since a refused turn persists nothing. Asserted in `test_stream_response_blocks_before_persisting_or_calling_agent`.

### 9/F-08 [P2] closed - Fail-closed guardrail blocks are silent

**File:** app/guardrails/service.py:130
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `validate_output` returns the fallback on a static-policy block, on `GuardrailProviderError`, and on any unexpected exception, with no logger and no metric in the module. The provider can fail on every request and the only symptom is users reporting that the assistant refuses everything, which is exactly the F-01 failure mode. Separately, when `GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR` is false this method does raise, contradicting the comment at `app/services/chat_service.py:229` that it always returns a string; the exception then surfaces to the client as a `ChatStreamError` naming `GuardrailProviderError`.
**Suggested fix:** Log a warning on each block and fail-closed branch with the rule name and provider status, never the response text. Correct or remove the inaccurate comment.
**Resolution:** Fixed 2026-09-20. Added a module logger to `app/guardrails/service.py` and a `logger.warning` on every block and fail-closed branch, carrying the stage and rule but never the response text. Provider failures log with `exc_info`. Third review found two named parts unrepaired. The inaccurate comment in `chat_service.py` is corrected: `validate_output` absorbs provider errors only while fail-closed is on, and raises otherwise. `GuardrailService.generate()` no longer duplicates the output branches at all — it delegates to `validate_output` (net -46 lines), which is why it had drifted out of sync and lost the logging.

### 9/F-09 [P2] closed - /api/v1/rag/query returns model output with no guardrails

**File:** app/api/routes/rag.py:52
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: security)
**Why it matters:** The route is authenticated but runs neither `validate_input` nor `validate_output`. This directly contradicts the premise recorded in the spec's Out of scope section, that chat is the only agent entrypoint today, which was the stated reason for not placing rails on the agent graph. That scoping decision should be revisited now that the premise is known to be false. The route also returns `str(exc)` in a 500 detail, leaking internal error text.
**Suggested fix:** Out of this feature's declared scope. Add a build-plan item to bring `/rag/query` under the same rails, and reassess rail placement when it is specced.
**Resolution:** Fixed 2026-09-20. `/api/v1/rag/query` now runs `validate_input` and `validate_output` with the same injected `GuardrailService` as the chat path, returning the configured refusal instead of a generated answer when input is blocked. The 500 handler no longer returns `str(exc)`; it logs the exception and returns a fixed message.

### 9/F-10 [P3] closed - Self-check prompt renders without the user turn

**File:** app/guardrails/providers/nemo_provider.py:305
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `check_output` passes only the assistant message, so `{{ user_input }}` in the self-check prompt renders empty and rule 6 ("should answer the user's request") cannot be evaluated.
**Suggested fix:** Pass both the user and assistant messages, as NeMo's `check_async` documents for this case.
**Resolution:** Fixed 2026-09-20. `GuardrailService.validate_output` and `GuardrailProvider.check_output` now take an optional `user_input`, and `NemoGuardrailProvider` prepends the user turn to the messages passed to `check_async`, so `{{ user_input }}` renders. `ChatService` and the RAG route both pass the user's query. Asserted by `test_output_guardrail_receives_the_user_turn`.

### 9/F-11 [P3] closed - Refusal text comes from a module singleton, not the injected service

**File:** app/services/chat_service.py:130
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The function-local import is correct as written and monkeypatching works, but the refusal message is read from the global `guardrails_config` rather than from the injected `GuardrailService`, so a dependency-injection override cannot control it. The integration test only passes because the stub blocks a message for which the global config also has a message. `guardrails_config` is frozen at first import, so environment changes need a restart.
**Suggested fix:** Expose `input_fallback_message` on `GuardrailService`, or attach it to `GuardrailInputBlockedError`, and hoist the import to module scope.
**Resolution:** Fixed 2026-09-20. Added an `input_fallback_message` property to `GuardrailService` and removed the function-local `guardrails_config` import from `ChatService`, which now reads the refusal from the injected service. A dependency override can control it.

### 9/F-12 [P3] closed - Debug-cleanup leftovers

**File:** app/agent/nodes/generate.py:31
**Found:** 2026-09-19 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `logger.debug(doc.metadata)` logs a raw dict as the log message with no event name. `app/api/routes/audit.py:36` reaches into the private `audit_service._session` (resolved by the F-03 deletion). Several touched files end without a trailing newline.
**Suggested fix:** Give the debug log an event name, or remove it.
**Resolution:** Fixed 2026-09-20. `logger.debug(doc.metadata)` in `app/agent/nodes/generate.py` now logs an `agent.generate.document` event with the metadata in `extra`. The private `audit_service._session` access was already removed with F-03.

### 9/F-13 [P1] closed - Guardrail LLM adapter discards stop and llm_params, so an off-format judge answer destroys the real answer

**File:** app/guardrails/providers/llm_adapter.py:73
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** NeMo invokes the judge as `generate_async(prompt, stop=stop, **llm_params)`, where the self-check action supplies the lowest configured temperature, a max-token cap, and task stop tokens. `GuardrailLLMAdapter.generate_async` accepts `stop` and swallows `**kwargs`, then calls `self._provider.complete(messages=..., model=...)`, which has no parameter for any of them. Independently confirmed: `OpenRouterProvider.complete` takes only `messages` and `model`. The judge therefore runs at the provider's default temperature with no stop sequence. `is_content_safe` inspects only the first two words and returns block for anything it does not recognize, so a prose answer such as "The response is acceptable." is treated as a violation. The reviewer demonstrated this against the project's real rails: "No." passed, while "The response should not be blocked.", a longer prose acceptance, and an empty string all produced BLOCKED. `ChatService` then replaces the answer with the fallback and persists it, so this feature's own data-integrity rule makes the correct answer unrecoverable. This is the F-01 consequence reached by a different root cause; F-08 covers only the absence of logging, not the unparseable-verdict path.
**Suggested fix:** Forward `stop` and the `llm_params` through `GuardrailLLMAdapter.generate_async` and `stream_async` into `LLMProvider.complete`/`stream`, extending the provider interface with those parameters. A cheaper partial mitigation is registering an `output_parser` for `self_check_output` that treats an unrecognized verdict as allow-with-warning, but that weakens fail-closed and needs an explicit decision.
**Resolution:** Fixed 2026-09-20. Added optional `temperature`, `max_tokens` and `stop` to `LLMProvider.complete` and `.stream` and both implementations, omitting unset values entirely rather than forwarding `None`. `GuardrailLLMAdapter` now translates NeMo's `stop` and `llm_params` into those arguments instead of discarding them, ignoring unknown kwargs so a NeMo upgrade cannot break the call. `tests/guardrails/test_llm_adapter_sampling.py` (3 tests) asserts forwarding, omission, and that unknown options are dropped. Residual risk: pinning temperature and stop makes a one-word verdict far likelier but cannot guarantee it, and an unrecognised verdict still fails closed. Changing that would weaken fail-closed and was not done.

### 9/F-14 [P3] closed - Config test pins the F-06 bug rather than the setting

**File:** tests/unit/guardrails/test_config.py:26
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `assert guardrails_config.provider == "nemo"` passes only because `_build_guardrails_config()` reads the non-existent `GUARDRAIL_PROVIDER` instead of `GUARDRAILS_PROVIDER`, so the lookup always falls back to its default. The assertion would still pass if the setting were deleted and cannot fail when an operator sets a different provider. It gives false confidence over the still-open F-06.
**Suggested fix:** Assert against an overridden setting, or remove the assertion as part of repairing F-06.
**Resolution:** Fixed 2026-09-20. Renamed to `test_guardrails_provider_defaults_to_nemo` with a docstring stating plainly that it proves only the default and cannot prove the setting is read. The switch itself is now covered by `test_settings_are_functional.py`.

### 9/F-15 [P3] closed - Maintainer note is rendered into the model-facing prompt

**File:** app/guardrails/rails/prompts.yml:5
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Three lines addressed to a human developer, explaining how `is_content_safe` parses the answer and warning against re-inverting the wording, sit inside `content:` and are therefore sent to the judge model on every self-check. A YAML comment above the block would never be rendered. Beyond wasted tokens, meta-instructions about answer inversion invite an explanatory reply, and F-13 shows a prose reply fails closed. This was introduced by the F-01 repair.
**Suggested fix:** Move those lines to `#` comments outside `content:`. The wording is already guarded in code by `tests/guardrails/test_rails_polarity.py`.
**Resolution:** Fixed 2026-09-20. Moved the maintainer note out of `content:` and into YAML `#` comments above the prompt, so it is no longer rendered into every judge prompt.

### 9/F-16 [P3] closed - rails/config.yml declares a judge model that is never used

**File:** app/guardrails/rails/config.yml:1
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The `models:` block naming `gpt-4o-mini` is dead, because `LLMRails` is constructed with the application's own provider adapter, which overrides the main model. The rails actually run on the configured `OPENROUTER_MODEL`. Someone tuning guardrail cost or quality will edit a file that has no effect.
**Suggested fix:** Delete the `models:` block and note in a comment that the judge model comes from the application LLM provider settings.
**Resolution:** Fixed 2026-09-20. Deleted the dead `models:` block from `app/guardrails/rails/config.yml` and replaced it with a comment explaining that the judge model comes from the application provider settings.

### 9/F-17 [P2] closed - GET /api/v1/guardrails/health called a method that does not exist

**File:** app/api/routes/guardrails.py:29
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The handler called `service.health_check()`, but `GuardrailService` has no such method; it lives on the provider. Independently confirmed by introspection. Every authenticated request therefore raised `AttributeError` and returned 500 — the endpoint had never worked. It shipped because F-02's repair was verified only through the OpenAPI schema and an anonymous 401, neither of which executes the handler body. Asserting that a route requires auth is not asserting that it works.
**Suggested fix:** Call `service.provider.health_check()`, or delete the route.
**Resolution:** Fixed 2026-09-20. Calls `service.provider.health_check()`. Added `tests/integration/test_guardrails_routes.py`, the first coverage this router has ever had, which executes the handler body. Mutation-checked: reintroducing the bug fails the test.

### 9/F-18 [P2] closed - /api/v1/rag/query could never return a successful response

**File:** app/api/routes/rag.py:90
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The `sources` comprehension emitted `score` and no `content`, while `RAGSource` requires `content` and `similarity_score`. Any query retrieving at least one chunk raised a `ValidationError` inside the handler. The route also passed `similarity_scores=` to `RAGQueryResponse`, which has no such field. The `sources` defect predates this work, but F-09 took ownership of the route and replaced `detail=str(exc)` with a fixed message, muting the only clue — and copied the non-existent `similarity_scores=` kwarg into the new refusal return, which proves that path was never executed.
**Suggested fix:** Supply `content`, rename `score` to `similarity_score`, and drop the phantom kwarg.
**Resolution:** Fixed 2026-09-20. Added `content=document.page_content`, renamed `score` to `similarity_score`, removed `similarity_scores=` from both constructors. Added `tests/integration/test_rag_routes.py` (5 tests) covering the success path, blocked input, output replacement, error redaction and auth. Mutation-checked: reintroducing the bug fails 2 of them.

### 9/F-19 [P3] closed - check_output ran NeMo's input rails as well as its output rails

**File:** app/guardrails/providers/nemo_provider.py:313
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: performance)
**Why it matters:** NeMo selects rails from message roles, so passing the user turn added for F-10 meant both input and output rails fired. Harmless only because `rails.input.flows` is empty; the moment an input flow is added, every output check would cost a second judge call and an input rail could block an output check, reported as an output violation.
**Suggested fix:** Pin `rail_types=[RailType.OUTPUT]`.
**Resolution:** Fixed 2026-09-20. `check_async` now pins `rail_types=[RailType.OUTPUT]`; the user turn still renders into the judge prompt.

### 9/F-20 [P3] closed - OpenAIProvider was left behind by the LLMProvider interface change

**File:** app/services/llm/providers/openai_provider.py:47
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** F-13 added keyword-only sampling parameters to the abstract `stream` and `complete` and to two of three implementations. `OpenAIProvider` was missed. Unreachable today because the factory only builds mock and OpenRouter providers, but wiring it would fail on the first guardrail judge call.
**Suggested fix:** Add the parameters, or delete the unused module.
**Resolution:** Fixed 2026-09-20. Both signatures updated; all three implementations now verified to match the interface.

### 9/F-21 [P3] closed - StreamChunk.is_final was False on the actual final chunk

**File:** app/services/llm/models.py:99
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The only producer of `is_final=True` was the guardrail refusal added for F-07; `final_chunk()` never set it. A reader trusting the field name to find the end of a stream would pick the refusal and miss every normal completion.
**Suggested fix:** Set `is_final=True` in `final_chunk()`.
**Resolution:** Fixed 2026-09-20. `final_chunk()` sets it; the route's ordering already tolerates it.

### 9/F-22 [P3] closed - Mid-file import papering over a circular dependency

**File:** app/api/dependencies.py:625
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The import sits mid-file because `app/guardrails/dependencies.py` imports back from this module. Hoisting it, the first thing any tidy-up would do, is an ImportError at startup, and nothing marked it as load-bearing.
**Suggested fix:** Document it, or break the cycle.
**Resolution:** Fixed 2026-09-20 with a comment stating why it cannot be hoisted. The cycle itself is left in place; breaking it means moving `get_llm_provider` to its own module, which is a wider refactor than this feature warrants.

### 9/F-23 [P3] closed - The highest-risk repairs added no coverage at their own layer

**File:** app/api/routes/rag.py
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `/rag/query` had no test at all, which is how F-18 stayed invisible. `app/api/routes/guardrails.py` had none either, which is how F-17 shipped. F-07's fix lives in `chat.py` but was asserted only at the `ChatService` layer, so the done frame itself — the entire point of the finding — went unchecked at the route.
**Suggested fix:** A route test per endpoint, and a done-frame assertion in the existing integration test.
**Resolution:** Fixed 2026-09-20. Added `tests/integration/test_rag_routes.py` (5) and `tests/integration/test_guardrails_routes.py` (3), both mutation-checked against their findings, and added `assert '"finish_reason":"content_filter"' in body` to `test_chat_stream_blocks_input_before_agent`.

### 9/F-24 [P0] closed - The API could not start: get_llm_provider returned None

**File:** app/api/dependencies.py:204 (now app/services/llm/factory.py)
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The factory handled `"mock"` and `"openrouter"` and then fell off the end, returning `None`. This checkout's `.env` set `LLM_PROVIDER=groq`, a provider that was never implemented. The `None` factory predates this work, but the lifespan hook added in this delta is what made it fatal: `get_guardrail_service()` built `NemoGuardrailProvider(llm_provider=None)`, whose `initialize()` raised, so the entire API failed to boot rather than just the AI paths. Independently confirmed by running the real lifespan.
**This corrects an earlier misdiagnosis of mine.** The three integration failures recorded through three rounds as "pre-existing and environmental, a cross-encoder exhausting the machine's paging file" were caused by this: `RAGChain` called `.complete()` on `None`. Proven by running them with a valid provider, where all three pass. The paging-file `OSError` was real but was a separate, earlier symptom of the per-request reranker construction fixed in F-04; after that repair the true cause was the `None` provider, and I carried the old explanation forward without re-testing it.
**Suggested fix:** Raise on an unsupported value instead of returning None.
**Resolution:** Fixed 2026-09-20. Provider construction moved to `app/services/llm/factory.py`, which raises `ValueError` naming the bad value and the supported set. `app/api/dependencies.py` re-exports the name so existing imports keep working. `.env` (untracked, local) changed from the unimplemented `groq` to `openrouter`; a backup was kept. `tests/unit/services/test_llm_factory.py` (7 tests) covers both providers and the fallthrough, including the literal `"groq"` value. `tests/conftest.py` now pins `LLM_PROVIDER=mock` so the suite never depends on a live paid API. Suite is now 376 passed, 0 failed.

### 9/F-25 [P2] closed - POST /api/v1/guardrails/test returned 500 for the case it exists to test

**File:** app/api/routes/guardrails.py:48
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The handler called `service.generate(...)` with no exception handling, and `generate` calls `validate_input` first, which raises `GuardrailInputBlockedError` on a violation. Demonstrating a blocked message is the endpoint's whole purpose, and it returned an unhandled 500. Same pattern as F-17: the handler body had no test.
**Suggested fix:** Return the configured refusal for a blocked input; map provider errors to 502.
**Resolution:** Fixed 2026-09-20. Blocked input returns the refusal as a normal 200 response mirroring the RAG route; `GuardrailProviderError` becomes a 502 with no internal detail. Three tests added that execute the handler body on the allowed, blocked and provider-failure paths.

### 9/F-26 [P3] closed - RailType/RailStatus imported three times in one file

**File:** app/guardrails/providers/nemo_provider.py:14
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The F-19 repair added a third redundant import of symbols the file already imported twice. Harmless, but it is the same leftover class F-12 was raised for.
**Suggested fix:** Keep the combined import, delete the other two.
**Resolution:** Fixed 2026-09-20. One combined import remains.

### 9/F-27 [P3] closed - The chat stream's real final chunk still had is_final False

**File:** app/services/chat_service.py:310
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** F-21 fixed the `final_chunk()` factory, which `ChatService` does not use. The normal terminal chunk was built literally and left `is_final` at its default, so on the chat path the field still marked only guardrail refusals — exactly the defect F-21 described. The repair had addressed the wrong construction site.
**Suggested fix:** Set `is_final=True` on the terminal chunk.
**Resolution:** Fixed 2026-09-20. Inert either way given the route's `message_id`-first ordering, but the field now means what its name says.

### 9/F-29 [P3] closed - Circular import between the API and guardrails dependency modules

**File:** app/api/dependencies.py:625
**Found:** 2026-09-20 by the builder while repairing F-28
**Why it matters:** F-22 documented this cycle rather than breaking it. It then broke a new test, which could not import `app.guardrails.dependencies` first without an ImportError. A hazard that only a comment protects will eventually bite.
**Suggested fix:** Move `get_llm_provider` out of the API layer.
**Resolution:** Fixed 2026-09-20. `app/services/llm/factory.py` now owns provider construction; `app.guardrails.dependencies` imports from there, `app.api.dependencies` re-exports for compatibility, and the mid-file import is an ordinary top-level one again. This supersedes F-22's comment-only repair.

### 9/F-30 [P1] accepted - Chat integration tests passed while the endpoint delivered a guardrail refusal

**File:** tests/integration/conftest.py:111
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `httpx.ASGITransport` does not run the application lifespan, so the startup hook never fired and the NeMo provider was never initialised. `check_output` then raised, `validate_output` failed closed, and every chat response the client saw was `GUARDRAIL_OUTPUT_FALLBACK_MESSAGE` rather than the model's answer. The three flagship tests assert on frame shapes -- `"token"`, `"finish_reason"`, `"prompt_tokens"` -- and a refusal frame satisfies every one of them. This feature's two headline contracts, that output rails govern the delivered response and that delivered text equals persisted text equals the model's answer, therefore had zero end-to-end coverage: the success path could have broken completely and the suite would have stayed green. It is the same blind spot that hid F-24 for four rounds, and the second time the builder declared these three tests sound without checking what the endpoint actually returned.
**Suggested fix:** Initialise the provider for integration tests and assert the delivered token equals the agent's answer.
**Resolution:** Fixed 2026-09-20. An autouse fixture in the integration conftest initialises and shuts down the real guardrail service. That alone was not enough: with `MockProvider` also acting as the judge, its stock prose reply is unparseable to `is_content_safe` and fails closed, so `MockProvider` now answers a self-check prompt with "no" -- a faithful double rather than one that silently converts every response into a refusal. `test_chat_stream_success` now asserts the delivered body contains the model's answer and neither fallback message. Verified by watching the assertion fail before the fix and pass after.

**Resolution (status change):** Accepted 2026-09-20 by the user's explicit decision in chat: "stop reviewing, complete 009 and move to 010". This does NOT mean unfixed. The defect is repaired and covered by tests described above, and the full suite passes at 486 tests. What is accepted is the absence of an independent re-review of that repair. Five review passes each found a real defect, two of them in repairs from the preceding pass, so a sixth was offered and declined. Anyone picking this up should treat the repair as builder-verified only.
### 9/F-31 [P1] accepted - A new LLM provider and HTTP pool were built for every request

**File:** app/services/llm/factory.py:23
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: performance)
**Why it matters:** `get_llm_provider` was uncached and `get_rag_chain` took it as a per-request dependency, so every `/chat/stream` and `/rag/query` constructed a fresh `OpenRouterProvider`, a fresh `AsyncOpenAI`, and a fresh `httpx.AsyncClient` that was never closed. The reviewer measured roughly 750 ms per construction across five consecutive runs, so this was steady-state cost, not a first-call warm-up: three-quarters of a second of dead latency on every AI request, a new TLS handshake each time, and a growing set of leaked pools. Exactly the defect class as F-04, in the module this work had just rewired, next to an already-cached sibling.
**Suggested fix:** Cache the factory.
**Resolution:** Fixed 2026-09-20. `@lru_cache(maxsize=1)`; settings are a process singleton so the key is constant. The factory tests clear the cache per test, and a new test asserts two calls return the same instance.

**Resolution (status change):** Accepted 2026-09-20 by the user's explicit decision in chat: "stop reviewing, complete 009 and move to 010". This does NOT mean unfixed. The defect is repaired and covered by tests described above, and the full suite passes at 486 tests. What is accepted is the absence of an independent re-review of that repair. Five review passes each found a real defect, two of them in repairs from the preceding pass, so a sixth was offered and declined. Anyone picking this up should treat the repair as builder-verified only.
