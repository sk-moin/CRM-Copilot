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
