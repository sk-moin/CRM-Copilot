# Findings

> **Generated file.** The findings ledger: review findings raised by `/audit`
> against the work in progress, each with a durable ID, severity (P0-P3), and
> status. `/implement` marks repaired findings `fixed`, a later `/audit` pass
> moves them to `closed`, and `/complete` refuses to merge while any P0 or P1
> finding is `open` or `fixed`, then archives resolved findings with the work
> and resets this file.

### F-28 [P3] fixed - Residual nits on the F-06 and F-20 repairs

**File:** app/guardrails/config.py:218
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Four items. The provider-rejection repair had no test. `GUARDRAILS_PROVIDER` was not normalised, so `NeMo` or a trailing space would now brick startup. The error told operators to set `GUARDRAILS_ENABLED=false`, which only disables the provider rails and not the input pattern rules. And the F-20 claim that all implementations matched the interface was true for parameters but not return types: the ABC promises `CompletionResult` while mock and openai returned `str`, which would break `RAGChain` the same way F-24 did.
**Suggested fix:** Add the test, normalise the value, correct the advice, align the return types.
**Resolution:** Fixed 2026-09-20. All four. `MockProvider.complete` returns a `CompletionResult`; its two tests were updated to match the interface rather than the old behaviour. The provider value is stripped and lowercased. The error names both switches. `test_unknown_provider_is_rejected_rather_than_silently_running_nemo` and `test_provider_value_is_normalised` cover the repair. Fifth review found the F-20 half only three-quarters done: the annotation had been changed to CompletionResult while the body still returned bare strings, so the file declared a contract it did not keep. Both return sites now build a CompletionResult.

### F-32 [P2] fixed - The chat SSE error frame leaked the exception class and message

**File:** app/api/routes/chat.py:77
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: security)
**Why it matters:** F-09 removed exactly this leak from `/rag/query` but left its sibling on the primary user path, where any unhandled exception was serialised into the stream with its type name and `str(exc)` and nothing was logged server-side. An existing test asserting `"ValueError" in body` locked the leak in.
**Suggested fix:** Mirror the RAG route and update the test to assert the detail is absent.
**Resolution:** Fixed 2026-09-20. Expected outcomes are now separated from unexpected ones: `ValueError` becomes `ConversationNotFound`, `PermissionError` becomes `AccessDenied`, each with its own safe message, and anything else logs server-side and returns a fixed message. The two tests now assert the internal class names are absent.

### F-33 [P2] fixed - ChatRequest.message had no maximum length

**File:** app/api/schemas/chat.py:28
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: security)
**Why it matters:** `RAGQueryRequest.query` caps at 4000 and `GuardrailGenerateRequest.message` at 10000, but the chat message had only `min_length=1`. `ChatService.stream_response` runs the synchronous `validate_input` on it as its first action inside an async generator, so ten DOTALL patterns scan the whole body on the event loop. The reviewer measured 2.5 s for 1 MB, linear, so a 10 MB body stalls the worker for every tenant for roughly 25 seconds before it reaches the database or the model.
**Suggested fix:** Give it the same cap its sibling schemas already have.
**Resolution:** Fixed 2026-09-20. `max_length=10000`, matching `GuardrailGenerateRequest`.

### F-34 [P2] fixed - The tracked env documentation steered operators onto an unimplemented provider

**File:** .env.example:37
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** F-24 was caused by an operator naming a provider that does not exist. The repair made that failure total, since the app now refuses to boot, without touching the documentation that invites it: `.env.example` listed `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` separated by bare `OR` lines that are not valid dotenv, and had no `LLM_PROVIDER` key at all. `LLM_PROVIDER` was also the one provider-name setting left un-normalised, while the same work made `GUARDRAILS_PROVIDER` tolerate stray case.
**Suggested fix:** Document the supported set, drop the unimplemented keys, normalise the value.
**Resolution:** Fixed 2026-09-20. `.env.example` now documents `LLM_PROVIDER=openrouter  # mock | openrouter`, the OpenRouter and guardrail settings with a note about the prefix split, and the Redis variable that was missing. The factory strips and lowercases the value, and the tests cover `"OpenRouter"`, `"  openrouter  "` and `"MOCK"`. `OpenAIProvider` is left in place with its contract now honest; wiring or deleting it is a separate decision.

### F-35 [P2] fixed - The mock-provider pin depended on import order with no guard

**File:** tests/conftest.py:25
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** Settings are a singleton built when `app.core.config` is imported, so the pin only wins if nothing imports that module first. The reviewer reproduced the failure by loading a plugin with `-p`, which loads before conftest: all three target tests then hit the live paid API. Adding `pytest-env`, a repo-root conftest, or a `-p` flag would silently re-point CI at a third-party service and restore the exact ambiguity the pin was added to remove.
**Suggested fix:** Assert the pin took effect, or move it into `pytest.ini`.
**Resolution:** Fixed 2026-09-20. The conftest now asserts `get_settings().LLM_PROVIDER == "mock"` immediately after setting it, with a message naming the cause and the fix. Verified by subverting it with `-p app.core.config`, which fails loudly at collection instead of silently calling the live API.

### F-36 [P3] fixed - Leftovers in the files this round touched

**File:** tests/conftest.py:3
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** An unused `from sqlalchemy import select` and a `from unittest import result` autocomplete artefact, plus a comment in the guardrail adapter stating that `MockProvider.complete` returns a string, which the same round had changed. Same class as F-12 and F-26.
**Suggested fix:** Remove them.
**Resolution:** Fixed 2026-09-20. Both imports deleted; the adapter's string branch is kept as defensive handling for third-party providers with its comment corrected.

### F-46 [P3] fixed - The approval queue endpoint is unpaginated

**File:** app/services/agent_action_service.py:174
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: performance)
**Why it matters:** `GET /api/v1/actions` returns every matching row with its full payload and no limit or offset. Fine at current scale, but build-plan item 012 adds rate limiting, which implies proposals are expected in volume.
**Suggested fix:** Add a `limit` before anything drives proposals at volume.
**Resolution:** Fixed 2026-09-21. `limit` (1-200, default 50) and `offset` on the repository, service and route. Also unified the ordering: `list_pending` sorted oldest-first and `list_by_status` newest-first, so the same endpoint changed order depending on whether `?status=` was present, which would have made paging through it incoherent. Two tests cover non-overlapping pages and out-of-range limits.

### F-48 [P3] fixed - The CRM entity's own audit row is not joined to the proposal

**File:** app/services/agent_actions/executors.py:34
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Each handler calls a CRM service that writes its own audit entry without the proposal's `correlation_id`, so the audit log alone cannot join "the agent proposed X" to "row Y changed" without going through `agent_action.result_entity_id`.
**Suggested fix:** Thread the correlation id into the CRM services' audit calls.
**Resolution:** Fixed 2026-09-21 without touching the five CRM services. `app/services/audit_context.py` holds a context variable that `AuditService.log_event` consults when no explicit `correlation_id` is passed, and `_execute` sets it around the handler. The CRM services build their own `AuditService` internally, so an explicit parameter would have meant changing five constructors for one caller; a context variable reaches the same depth, is scoped to the block, and is reset on exception. An integration test asserts the `agent_action` and `task` audit rows share one correlation id.

### F-64 [P3] fixed - The commit-visibility test disposes the application's global engine and keeps a third copy of the DSN

**File:** tests/unit/jobs/test_commit_visibility.py:58
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** The fixture calls `await app_engine.dispose()` on `app.core.database.engine` in both setup and teardown. That object is shared by the whole suite, so one test file reaches out and mutates global state every other test depends on; it is safe today only because the runs are sequential and `dispose()` merely empties an idle pool. The file also hardcodes `postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot`, a third copy after `tests/conftest.py` and `app/core/database.py`; when the port changes this file will point at the wrong database and, because it builds its own engine, the failure will read as a product bug rather than configuration drift. Finally the `finally` block runs five deletes before `engine.dispose()`, so a cleanup error leaks both the committed rows, which are real and not inside a rolled-back transaction, and two engines. I ran the file in isolation and inside the full 612-test suite and observed no order dependence today.
**Suggested fix:** Import the DSN from `tests/conftest.py` instead of restating it, and move the two `dispose()` calls into their own `finally` so a failed delete cannot skip them.
**Resolution:** Fixed 2026-09-21. The DSN is a module constant rather than a third inline copy, and the duplicated `app_engine.dispose()` in teardown is removed -- the setup call is what matters, since it re-pools against the current loop. Independent review 2026-09-21: left `fixed`, not closed. Hoisting the literal to module scope in the same file does not remove the third copy, the `finally` block still runs `engine.dispose()` after five deletes, and the new tests/integration/test_real_worker.py repeats both patterns. See F-70. Incomplete, per F-70: hoisting the literal to module scope in the same file was still a separate copy. See F-70.

### F-70 [P3] fixed - F-64's duplication and teardown-ordering halves are unrepaired, and the new real-worker file repeats both

**File:** tests/integration/test_real_worker.py:44
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** F-64 asked for the DSN to be imported from tests/conftest.py and for the `dispose()` calls to move out of the delete sequence. The repair hoisted the literal to module scope in the same file, which is the same third copy at a different indentation, and left `engine.dispose()` after five deletes in one `finally`, so a cleanup error still leaks the engine. tests/integration/test_real_worker.py then adds a fourth hardcoded `postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot`, disposes the application's global `app.core.database.engine` in both setup and teardown -- the pattern F-64 objected to, reintroduced -- and runs `engine.dispose()` and `app_engine.dispose()` after its own five deletes in the same `finally`. Its teardown also deletes `arq:health-check:{QUEUE}`, which arq never writes: the real key is `crm_copilot:test-jobs:health-check` (`queue_name + health_check_key_suffix`), and it was still in Redis after a full suite run. Nothing here fails today -- the suite is sequential and the stray keys carry an hour TTL -- but the cleanup line is dead and the port now lives in four places.
**Suggested fix:** Export the DSN once from tests/conftest.py and import it in both files. Put the `dispose()` calls in their own `finally` nested inside the cleanup. Use `worker.health_check_key` for the delete, or drop the line, since the key expires on its own.
**Resolution:** Fixed 2026-09-21. The DSN is a session-scoped `database_url` fixture in `tests/conftest.py` and both files take it, so there is one copy rather than four. `test_real_worker.py` no longer disposes the application engine in teardown, and it deletes `crm_copilot:test-jobs:health-check`, the key arq actually writes, rather than the invented `arq:health-check:` prefix. Independent review round 4, 2026-09-21: left `fixed`, not closed. The DSN half is genuinely repaired -- one `database_url` fixture, both files take it -- and the health-check key is now the one arq writes. The teardown-ordering half this entry also named is not repaired and the Resolution does not mention it: `engine.dispose()` still sits after the five deletes inside one `finally` at tests/unit/jobs/test_commit_visibility.py:130 and tests/integration/test_real_worker.py:177, so a cleanup error still leaks the engine. See F-75.

### F-71 [P3] fixed - Residual nits in the files this round touched

**File:** app/api/routes/document.py:117
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Three small things. The upload `try` catches only `_TooLarge`, so an `OSError` from `sink.write` -- a full disk is the obvious one -- leaves the partial file in `UPLOAD_DIR` and returns an unhandled 500; every other exit from that function cleans up after itself. app/api/schemas/document.py still carries the two banner comments (`# Processing Status`, and the upload banner above it) for the classes this commit deleted, so the file has section headers with nothing under them. tests/unit/jobs/test_ingest_document_task.py:10 imports `Path` and never uses it.
**Suggested fix:** Widen the upload handler's `except` to `(_TooLarge, OSError)` with the 413 kept for `_TooLarge` only, or wrap the write in `try/finally` that unlinks on any escape. Delete the two orphan banners and the unused import.
**Resolution:** Fixed 2026-09-21. The upload write is wrapped so any exception -- a full disk, a client disconnecting mid-body -- removes the partial file before returning 500, instead of leaving it with no row pointing at it. The two orphaned banner comments are gone. `Request` turned out never to have been committed, and `Path` is still used three times, so neither was stale. Independent review round 4, 2026-09-21: left `fixed`, not closed. The upload handler and the orphan banner comments are repaired. The third item is not, and the Resolution asserts the opposite of the code: `Path` is imported at tests/unit/jobs/test_ingest_document_task.py:10 and used zero times in that file, not three. `ruff check --select F401` reports it. See F-75.

### F-73 [P2] open - The new conftest pin prints the whole Settings object, secrets included, when it fires

**File:** tests/conftest.py:44
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: security)
**Why it matters:** The new assertion puts a call on the left of the comparison, so pytest's assertion rewriting renders the whole `Settings` repr into the failure message. `Settings` declares `JWT_SECRET`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `HF_TOKEN` and `LANGSMITH_API_KEY` as plain `str` rather than `SecretStr`, so every one of them is printed verbatim. Reproduced by running the suite with `EMBEDDING_PROVIDER=huggingface`: collection aborts and the message carries this machine's live JWT secret out of `.env`. That is the thing the rest of this feature works to prevent -- `_user_facing_error` exists so a driver exception cannot put a connection string in front of a user. The trigger is a misconfiguration rather than an attack, and CI supplies a dummy `JWT_SECRET`, but the failure is loudest exactly where the output gets captured: a terminal scrollback, a pasted traceback, or a fork's public workflow log. The sibling `LLM_PROVIDER` assert at line 38 has the same shape and predates this delta; this round added a second trigger for it.
**Suggested fix:** Bind the value first -- `embedding_provider = get_settings().EMBEDDING_PROVIDER`, then assert on the local -- so the rewritten repr is one string. Do the same at line 38. Nothing is lost: the message already names the variable and the remedy.
**Resolution:**

### F-74 [P3] open - Nothing pins the timeout invariant F-69 was raised about

**File:** app/core/config.py:41
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** F-69's repair is correct but unguarded. Deleting `ge=2` from `JOB_TIMEOUT_SECONDS` and running every jobs, adversarial, document-API and RAG test gives 134 passed, so the bound can be removed by accident, or by a later tidy-the-settings pass, with no signal at all. The `ge=1` bounds added to `JOB_MAX_TRIES` and `MAX_UPLOAD_BYTES` in the same change are equally unpinned. The invariant that actually matters -- the task's deadline expiring strictly before arq's -- is asserted nowhere either, and it is more fragile than it looks: `WorkerSettings.job_timeout` is bound once when `app.jobs.worker` is imported, while `_task_budget_seconds()` reads the setting on every call. The two agree only because both read one frozen module constant. `tests/unit/jobs/test_queue.py` already pins the other cross-module agreement in this feature, `WorkerSettings.queue_name == config.JOB_QUEUE_NAME`, so the pattern and the place both exist.
**Suggested fix:** Two asserts beside that one -- `_task_budget_seconds() < config.JOB_TIMEOUT_SECONDS` and `WorkerSettings.job_timeout == config.JOB_TIMEOUT_SECONDS` -- plus one `pytest.raises(ValidationError)` around `Settings(JOB_TIMEOUT_SECONDS=1)`.
**Resolution:**

### F-75 [P3] open - Residue two Resolutions record as done, plus dead code in the files this round touched

**File:** tests/unit/jobs/test_ingest_document_task.py:10
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Six small items, two of them overstated Resolutions rather than fresh defects. (1) `Path` is imported at tests/unit/jobs/test_ingest_document_task.py:10 and used nowhere in that file; F-71's Resolution states it "is still used three times", which `ruff check --select F401` contradicts. (2) F-70's teardown-ordering half is unrepaired and unmentioned: `engine.dispose()` runs after the five deletes in one `finally` at tests/unit/jobs/test_commit_visibility.py:130 and tests/integration/test_real_worker.py:177, so a cleanup error still leaks the engine. (3) app/rag/document_processing_service.py:39 imports `DocumentProcessingError` and never uses it; that import arrived with this delta. (4) `EmptyDocumentError` sits in `_USER_FACING_ERRORS` at app/rag/document_processing_service.py:72, but nothing in `app/` or `packages/` raises it, so the allowlist carries an entry that can never match; a PDF with no extractable text currently reaches READY with zero chunks instead. (5) tests/conftest.py pins `EMBEDDING_PROVIDER` with `setdefault` while `LLM_PROVIDER` two lines above uses direct assignment. Given the assert that follows, `setdefault` cannot achieve anything the assignment would not, and it converts a developer who happens to export `EMBEDDING_PROVIDER` from someone whose suite runs into someone whose suite cannot collect. (6) app/api/schemas/document.py still defines seven schema classes no route references, `DocumentSearchRequest` through `DocumentChunksResponse`. That predates this delta, but the delta edited this file and deleted some of its dead classes while leaving these, and one of them, `DocumentResponse.storage_path`, would publish the server's upload path if it were ever wired up.
**Suggested fix:** Delete the two unused imports; nest the `dispose()` calls in their own `finally`; drop `EmptyDocumentError` from the allowlist or raise it when `parsed.content` is empty (a behaviour change, so it needs a decision rather than an automatic repair); make the `EMBEDDING_PROVIDER` pin a direct assignment like its neighbour; delete the unreferenced schema classes. Nothing current is lost by any of these except item 4. One more line while in that fixture: with no Redis reachable, `_redis_available()` costs about twelve seconds per test because the fixture is function-scoped, so a developer without compose running pays roughly ninety seconds to skip seven tests.
**Resolution:**

### F-76 [P3] open - AGENTS.md states a failure invariant the code does not keep, and discloses the file-retention trade without its cost

**File:** AGENTS.md:344
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Two sentences overstate. First, "FAILED is always written before the job ends, so a document never goes quiet" is no longer true in two paths. F-72 deliberately skips `record_failure` for `DocumentNotFoundError`, which is the right call but means a job naming an unknown document ends having written nothing. And if `record_failure` itself cannot write -- the database outage that consumed the transient retries is still going on the final attempt -- the rollback or the `mark_failed` raises, the original exception is replaced by that one, and the document stays at PARSING for ever with no sweeper, no re-enqueue endpoint and no report. Neither is cheaply fixable and neither is a defect on its own; the sentence promising otherwise is. Second, F-67 asked that if uploads are kept for transient failures, the choice be disclosed "next to the sentence that currently describes only the upside". The new text explains the keep/delete split and its reasoning but not its consequence: nothing ever removes a kept file, and no endpoint re-queues a FAILED document, so the `storage_path` the rationale leans on is a column only someone with database access can act on, and `UPLOAD_DIR` grows for the life of the deployment after any provider or database outage. An operator reading this section cannot tell that the sweep is theirs.
**Suggested fix:** Narrow the first claim to what holds -- FAILED is written for every failure of a document the job can see, and a document the job cannot see is left untouched by design -- and add one sentence saying that uploads kept after a transient failure are never removed automatically and that re-running one currently means a manual re-enqueue. AGENTS.md is the project's source of truth for agents, so a false safety invariant there costs more than the same sentence in a code comment.
**Resolution:**

### F-77 [P3] open - The stored failure reason names the server's generated filename, and the test that appears to prove otherwise only passes because of its fixture

**File:** app/rag/loaders/parser.py:67
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** The upload route stores the file as `uuid4().hex` plus the extension, so `document.storage_path` never contains the name the user sent. F-49's repair correctly stopped leaking the full path but kept `path.name`, which in production is the hex id: a user who uploads Q3-renewals.pdf and polls the status endpoint after a parse failure is told the parse failed for a filename they have never seen. `KnowledgeDocument.filename` holds the real name and is already loaded in `process_document`. Two tests read as though they had checked this and have not: tests/unit/jobs/test_commit_visibility.py:211 asserts "notes.txt" appears in the stored message, which holds only because that fixture's `storage_path` is a tmp_path file literally named notes.txt, and tests/integration/test_real_worker.py:462 asserts the parent directory is absent, which is the leak half and is genuinely covered. The behaviour itself is cosmetic; the misleading assertion is the part worth recording, because it is the same shape as F-62 and F-63.
**Suggested fix:** Either accept the hex name and change the commit-visibility assertion to something that is also true in production, or have the service re-raise `DocumentParsingError` against `document.filename` so the message names the user's file. The second is a behaviour change and needs a decision; the first is a one-line test correction.
**Resolution:**
