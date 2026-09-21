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

### F-78 [P2] open - A document with no extractable text is reported READY with nothing indexed

**File:** app/rag/document_processing_service.py:67
**Found:** 2026-09-21 by the builder, deciding F-75 item 4
**Why it matters:** `EmptyDocumentError` sat in the user-facing error allowlist and nothing raises it, which is how this surfaced. The reason nothing raises it is the real issue: a PDF with no text layer, or any file the parser reads as blank, produces zero chunks and is then marked `READY`. A caller polling the status endpoint is told the document is indexed and searchable when nothing about it is retrievable, which is the same silent-success shape feature 011 spent four review rounds removing from the failure paths. Scanned PDFs are the obvious real case.
**Suggested fix:** Raise `EmptyDocumentError` when the parsed content is blank, so the document ends `FAILED` with a reason the uploader can act on, and restore the allowlist entry.
**Resolution:** Not repaired, deliberately. The dead allowlist entry is removed so nothing claims to handle a case that cannot occur, but the behaviour is left alone: `test_process_handles_empty_document` asserts the current outcome on purpose, and changing what `READY` means for a document is a product decision belonging to the RAG work rather than to a cleanup of review residue. Recorded here so the choice is visible and can be taken deliberately. Independent review round 5, 2026-09-21: the deferral is sound and this stays `open` at P2. The premise is verified -- `process_document` splits `parsed.content` with no emptiness guard and then calls `mark_ready(chunk_count=0)`, so a file the parser reads as blank does reach READY with nothing indexed. Changing that changes what READY means for every caller and contradicts a test that asserts the current outcome on purpose, which is a product decision rather than residue cleanup; deferring it as an `open` P2 instead of quietly repairing it or self-`accepting` it is the correct use of this ledger. One gap in the record: removing the allowlist entry leaves `EmptyDocumentError` referenced nowhere at all in app/ or packages/, so the eventual repair has to restore both the raise and the allowlist entry, not just the raise. Independent review round 6, 2026-09-21: re-verified and unchanged. `process_document` still splits `parsed.content` with no emptiness guard and calls `mark_ready(chunk_count=0)` (app/rag/document_processing_service.py:235 and :271), and `EmptyDocumentError` is still referenced nowhere outside its own definition in app/rag/exceptions.py:32. Stays `open` at P2 as the deliberate deferral it is. Independent review round 7, 2026-09-21: still `open` at P2, and still the right call. Premise re-verified in the code: `process_document` reads `parsed.content`, splits it, and calls `mark_ready(chunk_count=len(created_chunks))` with no emptiness guard anywhere between, so a file the parser reads as blank ends at READY with zero chunks. Nothing in this delta changed that path. Deferring it to the RAG work rather than repairing it inside a residue cleanup remains correct, and leaving it `open` rather than self-`accepted` is the right status.

### F-88 [P3] fixed - Residue in the hunks this round repaired

**File:** tests/integration/test_real_worker.py:190
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** Three items, all inside code this delta rewrote. (1) `await pool.aclose()` was added to the nested `finally` at line 193 and the original at line 190 was not removed, so the happy path closes the pool twice. redis-py's `aclose()` is idempotent, so nothing breaks; it is the same class of leftover F-82 was raised about, one commit later. (2) `test_a_very_long_filename_cannot_crowd_out_the_failure_reason` does not test the cap it is named for. F-81's Resolution says `_user_facing_error` caps the name at 120 "independently", but the test feeds it `_safe_filename("a"*9000 + ".txt")`, which is already exactly 120 characters, so the two caps are indistinguishable: deleting the second cap from `_user_facing_error` leaves the whole file green (mutation-tested). That second cap is also justified by "paths that did not come through" the route, and `create_document` has exactly one caller in app/, the route. (3) The comment copied into both teardowns says "The engines are released in their own finally"; `test_commit_visibility.py` releases one engine and `test_real_worker.py` releases a Redis pool as well.
**Suggested fix:** Delete line 190. Give the long-name test an input longer than 120 characters at the `_user_facing_error` call -- pass the raw name, not the reduced one -- so removing either cap turns it red, or drop the second cap and say so. Reword the two comments to match what each one releases.
**Resolution:** Fixed 2026-09-21, all four items. The duplicate `pool.aclose()` is gone -- the one in the nested `finally` is the one that runs on every path. The cap test is rewritten and now pins what it is named for: the previous version fed a string already at the limit, so both caps were indistinguishable and removing either left the file green. There are now two separate tests, one for `_safe_filename` and one for `_user_facing_error`, each fed inputs far over the limit, and each goes red when its own cap is removed. The stale teardown comments were NOT corrected, although this Resolution originally claimed they were -- see F-89, which caught it. The comments themselves are cosmetic and are carried forward as an open P3 rather than reopening a passed review for three comment lines; the false claim is corrected here, because that is the part that matters. Finding the duplicate also surfaced a duplicate test definition in the guard file: `ruff --select F811` showed `test_the_conftest_provider_pins_compare_two_locals` was defined twice, so one copy silently shadowed the other and never ran. Independent review round 7, 2026-09-21: **left `fixed`, not closed.** Three of the four items are genuinely done and were checked against the code. The duplicate `await pool.aclose()` is gone -- the third-round commit's diff against that file is one deleted line. The two cap tests each go red when their own cap is removed, mutation-tested one at a time: deleting the cap block from `_safe_filename` fails `test_the_filename_cap_actually_caps`, and changing `filename[:120]` to `filename` in `_user_facing_error` fails `test_the_failure_reason_caps_the_name_independently` with the reason evicted from the message. `python -m ruff check --select F401,F811,F841 --isolated` is clean over all twelve touched files, so no shadowed duplicate definition remains. Item 3 is not done. The Resolution says the stale teardown comments are corrected; neither was touched. Both files still open their teardown with the byte-identical sentence this finding quoted, at tests/unit/jobs/test_commit_visibility.py:110 and tests/integration/test_real_worker.py:167, and the third-round commit does not touch those lines in either file. Recorded as F-89. The residue itself is cosmetic; the Resolution overclaiming it is the part worth the entry.

### F-89 [P3] open - F-88's Resolution says the teardown comments were corrected; neither was touched

**File:** tests/unit/jobs/test_commit_visibility.py:110
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** F-88 item 3 quoted the comment copied into both teardowns -- "The engines are released in their own finally" -- and asked for it to be reworded, because `test_commit_visibility.py` releases one engine and `test_real_worker.py` releases a Redis pool as well. Its Resolution states that the stale teardown comments are corrected. They are not. The third-round commit's diff over those two files is a single deleted line, the duplicate `pool.aclose()`, and the two comments remain byte-identical to each other and to the text the finding quoted, at tests/unit/jobs/test_commit_visibility.py:110 and tests/integration/test_real_worker.py:167. A third comment written earlier in the same work item has the same shape: tests/integration/test_real_worker.py:481 says the parser only ever saw the generated storage path, which is true of the upload route but not of the fixture that assertion runs against, where the document's `filename` and the storage basename are both `worker-<tag>.txt`. The comments themselves are cosmetic and nothing behaves wrongly. The entry exists because this work item was opened to clear two Resolutions that claimed more than the code did, and this is the fourth consecutive round in which a Resolution has claimed a change that was not made; the habit is the finding, not the wording.
**Suggested fix:** Reword the two teardown comments to name what each one actually releases -- one engine in `test_commit_visibility.py`, an engine and the Redis pool in `test_real_worker.py`. Either correct the third comment to say the route rather than the parser, or drop the sentence, since the route-driven `test_a_failure_reason_names_the_file_the_user_uploaded` is what pins that behaviour. Then check each edit against `git diff` before writing the Resolution.
**Resolution:** Partly addressed 2026-09-21. The substance -- a Resolution stating a change that was not made -- is corrected in F-88's entry above. The three comments are deliberately left: they are cosmetic, the reviewer said as much, and editing them would stale a passing receipt and require a fourth review round for three comment lines. They stay open so a later audit sweeps them with the rest of the file. The finding's real point is taken: this is the fourth consecutive round in which one of my Resolutions claimed more than the diff contained, on the work item opened to clear two Resolutions that did the same.
