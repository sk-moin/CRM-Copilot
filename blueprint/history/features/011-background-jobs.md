# Feature: Background Jobs

**From build-plan:** feature 011
**Build attempt:** 1
**Branch:** feature/background-jobs
**Status:** verified

## Goal

Move document ingestion off the request path onto a durable queue, and make its
progress visible.

Today `POST /api/v1/documents/upload` parses, chunks, embeds and indexes the
file inside the request. Embedding a large PDF on CPU takes minutes, so the
client waits, the worker is blocked, and a dropped connection loses the work
entirely with a half-written document left behind.

Feature 005 already anticipated this: `KnowledgeDocument` carries
`processing_status` with a six-state lifecycle, and the repository already has
`mark_processing`, `mark_ready` and `mark_failed` driving `UPLOADED → PARSING
→ READY` or `FAILED` with timestamps, `chunk_count` and `error_message`. The
status machinery is real; what is missing is that it all happens inside the
request, so nobody can observe it and a dropped connection loses it.

## In scope

- An arq worker backed by the Redis already used for refresh tokens.
- A task registry with one real task: document ingestion. Not a framework for
  hypothetical future tasks.
- `POST /documents/upload` enqueues and returns `202 Accepted` with the
  document id instead of blocking.
- The ingestion task drives `processing_status` through its real lifecycle and
  records `processing_started_at`, `processed_at`, `chunk_count` and, on
  failure, `error_message`.
- `GET /documents/{id}/status` so a client can poll.
- Retries on transient failure, with a terminal `FAILED` state that does not
  retry forever.
- A `worker` service in docker-compose.
- Tests at each layer, including tenant isolation on the status endpoint.

## Out of scope

- **Eval runs.** Named on the build-plan line, but feature 014 does not exist,
  so there is nothing to enqueue. Adding a task type with no caller is
  machinery for a hypothetical.
- **A generic `Job` table.** `KnowledgeDocument` already models the status of
  the one real job type, and arq keeps its own job state in Redis. A second
  registry would need reconciling with both.
- Scheduled or recurring jobs, priorities, fan-out, dead-letter queues,
  cancellation, or a worker admin UI. No current requirement.
- Moving guardrail or agent calls off the request path. They are interactive;
  the user is waiting by design.
- Websocket or SSE push for progress. Polling is enough for an upload, and the
  status endpoint is what a push layer would read anyway.

## Build loop

`workflow.stepReview` is `feature`: implement all steps, then present one
review packet. `workflow.checkpointCommits` is `disabled`.

## Build steps

- [x] **1. Worker settings and the arq entry point.**
  `app/jobs/worker.py` with an arq `WorkerSettings` pointing at `REDIS_URL`,
  and `app/jobs/queue.py` exposing an enqueue helper that opens and reuses one
  arq Redis pool. Register the queue name explicitly rather than relying on
  the default, so a stray worker on a shared Redis cannot pick up this
  project's jobs. The dev Redis on this machine is shared with an unrelated
  container.
  *Done when:* `arq app.jobs.worker.WorkerSettings` starts against the local
  Redis and reports the registered task, and a unit test asserts the enqueue
  helper targets the configured queue.

- [x] **2. The ingestion task.**
  `app/jobs/tasks/ingest_document.py` wrapping the existing
  `DocumentProcessingService.process`. The task owns its own database session,
  because the request that enqueued it is long gone. It must be safe to run
  twice: arq retries, and a task that half-completed must not duplicate chunks.
  *Done when:* running the task directly produces the same document and chunks
  as the current inline path, and running it twice for one document leaves one
  set of chunks.

- [x] **3. Status lifecycle observable from outside the request.**
  Correcting this spec's first draft: `DocumentProcessingService.process`
  already calls `mark_processing` and `mark_ready`, and already catches and
  calls `mark_failed`. The lifecycle is not missing. What is missing is that
  it is invisible, because the whole thing completes before the response is
  sent. This step therefore verifies the transitions survive the move to a
  worker and commit at each stage, rather than inventing them.
  The unused `CHUNKING` and `EMBEDDING` states are deliberately left unwritten:
  `PARSING` already means "in progress" to a polling client, and two more
  states would be cosmetic.
  *Done when:* a test running the task observes `PARSING` committed and
  visible from a second session while work is still in flight, then `READY`
  with `chunk_count` and `processed_at`; a failing parse settles on `FAILED`
  with a message and no chunks.

- [x] **4. Upload enqueues instead of processing.**
  The route persists the file and the `KnowledgeDocument` row, enqueues the
  task, and returns `202` with the document id and status. The temporary file
  must outlive the request, since the worker is a different process: write it
  to a configured upload directory rather than `NamedTemporaryFile`, and let
  the task delete it when it finishes.
  *Done when:* the route returns 202 without embedding anything, the file is
  still readable after the request ends, and the enqueued job id is recorded.

- [x] **5. The status endpoint.**
  `GET /api/v1/documents/{id}/status` returning status, timestamps,
  `chunk_count` and `error_message`, tenant-scoped through the repository.
  *Done when:* route tests execute the handler on a pending, ready and failed
  document, another tenant gets 404, and an unauthenticated request gets 401.

- [x] **6. Failure and retry behaviour.**
  Cap retries so a document that cannot be parsed stops rather than looping.
  On the final attempt write `FAILED`; on earlier attempts let arq retry.
  *Done when:* a task that always raises ends `FAILED` after the configured
  attempts rather than retrying indefinitely, and a task that fails once then
  succeeds ends `READY`.

- [x] **7. Compose service and documentation.**
  A `worker` service in docker-compose running the same command a developer
  would, and the commands section updated. Add `arq` to `requirements.txt`.
  *Done when:* the worker service starts and picks up an enqueued job, and
  `AGENTS.md` documents how to run the worker locally.

## Files / areas

| Path | Change |
|---|---|
| `app/jobs/__init__.py`, `worker.py`, `queue.py` | New: worker settings, enqueue helper |
| `app/jobs/tasks/ingest_document.py` | New: the one real task |
| `app/api/routes/document.py` | Upload returns 202; new status endpoint |
| `app/api/schemas/document.py` | Enqueued and status responses |
| `app/core/config.py` | `UPLOAD_DIR`, queue name, retry limit |
| `app/rag/document_processing_service.py` | Status transitions; idempotent re-run |
| `docker-compose.yml`, `requirements.txt`, `AGENTS.md` | Worker service, `arq`, docs |
| `tests/...` | Unit, task, route, adversarial |

## Data / contracts

No new tables. The existing `KnowledgeDocument` columns carry the job state:

- `processing_status` — `UPLOADED` on enqueue, `PARSING` while the worker
  holds it, then `READY` or `FAILED`. `CHUNKING`, `EMBEDDING` and `COMPLETED`
  exist in the enum and are deliberately not written; see build step 3.
- `processing_started_at` — set when the task picks the job up, not at upload.
- `processed_at`, `chunk_count` — set on success.
- `error_message` — set on terminal failure, cleared on a successful retry.

**Locked rules**

- **The queue name is explicit.** The dev Redis is shared with an unrelated
  container; the default queue name would let jobs cross between them.
- **Re-running a task must not duplicate chunks.** arq retries, and a worker
  killed mid-embed will be retried.
- **The worker owns its session.** Nothing from the request context may be
  passed into a task; only JSON-serialisable arguments.
- **Tenant scope comes from the stored document**, not from task arguments.
- **A failed job is terminal and visible**, never a silent disappearance.

## Testing

`alembic upgrade head && python -m pytest` with Postgres on 5433 and Redis.
Baseline at spec time: 583 passed, 0 failed.

Tasks are tested by calling them directly with a stub context rather than by
running a worker: an in-process worker in the suite would make failures
ambiguous between the task and the harness.

## Notes for the AI

- Redis is already a dependency and `get_redis` is loop-aware via
  `reset_redis`; arq opens its own pool, which needs the same treatment in
  tests.
- `tests/conftest.py` pins `LLM_PROVIDER=mock`. Embeddings are separate:
  `EMBEDDING_PROVIDER` defaults to `huggingface`, so any test that really
  embeds will load a model. Use the mock embedding provider that already
  exists at `app/rag/embeddings/mock_embedding_provider.py`.
- Follow the established error convention: known outcomes get typed safe
  messages, unexpected ones log server-side and return a fixed message.
- Route tests must execute the handler body.
- `alembic revision --autogenerate` is trustworthy again as of the previous
  commit. If it reports drift, that is a real change, not pre-existing noise.

## Open questions

None blocking. One judgement call: uploads currently go to
`NamedTemporaryFile`, which is process-local and deleted on close, so the
worker could not read it. This introduces a configured `UPLOAD_DIR` on local
disk. That is correct for a single host and wrong for more than one; object
storage is the real answer and belongs with a deployment decision, not here.
Recorded rather than silently assumed.


## Independent review

Four independent review passes ran against this feature (adapter `claude`,
model `claude-opus-5[1m]`, context `fresh subagent`, execution `automatic`).
The fourth passed. The three before it did not, and what they found is the
real record of this feature:

| Pass | Target | Verdict | What it found |
|---|---|---|---|
| 1 | b6ec1f5 | changes-requested | Raw exception text served by the status endpoint (P1), plus 8 more. Noted that nothing in the suite proved any of the new commits actually commit. |
| 2 | d8df905 | changes-requested | A job outliving `job_timeout` was stranded at PARSING (P1) -- the same defect as F-58, in the adjacent path a full repair pass had just missed. |
| 3 | c9c06ab | changes-requested | That repair had relocated the defect rather than removed it (P1): the deadline expires by cancelling, so the rollback never ran and the failure was recorded on a dirty session. Also that removing the upload delete for every failure created an unbounded parking vector (P1). |
| 4 | 20ba1ea | **passed** | Closed F-59, F-60, F-66, F-67, F-68, F-69, F-72. Five new P2/P3 findings remain open in the ledger. |

Three separate defects of one class -- a job failing without recording
anything, leaving the document at PARSING with its file orphaned -- were found
across passes 2, 3 and 4. None was visible to any unit test, because every
job test called the task directly with a hand-built `ctx` and arq's own
control flow never participated. `tests/integration/test_real_worker.py`
exists because of that, and the class stopped recurring once it did.

Pass 4's receipt, verbatim:

**Status:** passed
**Target commit:** 20ba1ead726b31c19c0893c8343fc48d1639be2a
**Base commit:** 4cbf4ca6753156bdf6c100a80b0d0b8b488f70e4
**Base ref:** main
**Spec hash:** 2c1b64a708e07fdbd61b2d56fea60947d56b634bb32d8733d968ac9fadff9b46
**Prepared by:** claude
**Builder model:** claude-opus-5[1m]
**Requested reviewer:** claude
**Requested model:** runtime default (exact model not known until reviewer starts)
**Requested execution:** automatic
**Requested at:** 2026-09-21T03:00:00Z
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** claude
**Reviewer model:** claude-opus-5[1m]
**Reviewer context:** fresh subagent
**Actual execution:** automatic
**Reviewed at:** 2026-09-21T11:40:00Z
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

### Commands

- `git diff 4cbf4ca..20ba1ea` and `git diff --stat 4cbf4ca..20ba1ea` (29 files, +3195/-137): pass
- `alembic upgrade head` (Postgres 5433): pass
- `python -m pytest -q -p no:warnings`, no `EMBEDDING_PROVIDER` override: pass, 618 passed, 0 skipped, 311s
- Mutation: drop the rollback in `DocumentProcessingService.record_failure`, rerun the two real-worker timeout tests: pass (both go red, the second with `PendingRollbackError`), reverted
- Mutation: invert `if delete_source and not transient`, rerun the two upload-retention tests: pass (both go red), reverted
- Mutation: drop the `DocumentNotFoundError` guard in the task, rerun the adversarial and unit job tests: pass (the cross-tenant test goes red, 10 others still pass), reverted
- Mutation: drop `ge=2` from `JOB_TIMEOUT_SECONDS`, rerun jobs + adversarial + document-API + RAG tests: 134 passed, so the bound is unpinned, reverted
- `CI=true TEST_REDIS_URL=redis://localhost:6399 python -m pytest tests/integration/test_real_worker.py -k ingests`: pass (errors with the intended RuntimeError rather than skipping)
- `EMBEDDING_PROVIDER=huggingface python -m pytest --collect-only tests/unit/jobs`: pass (aborts loudly, does not load sentence-transformers) — and produced the evidence for F-73
- `ruff check --select F401,F811,F841 --isolated` over the delta's files: pass, three dead-import hits
- Typecheck, lint, coverage, security scan, browser tests: unavailable (none configured; see Remaining risk)

### Evidence

- F-66: `record_failure` rolls back first and is invoked outside the `asyncio.timeout` block, so the rollback cannot itself be cancelled by the deadline that caused it; the double rollback on the ordinary path is a no-op on a clean session, and the only caller is the task, which owns its session.
- F-67: every exception `DocumentParser.parse` can raise is wrapped in `DocumentParsingError` (app/rag/loaders/parser.py:95-99), so the attacker-controlled loop the finding described always lands in the deterministic branch and the file is deleted; `transient` is assigned at ingest_document.py:199 on every path that reaches its use at :237.
- F-72: `get_by_id` and the `DocumentNotFoundError` raise happen before `mark_processing`, so the skip cannot leave a document at PARSING; `create_document` commits before the route enqueues, there are no read replicas, and no document-delete endpoint exists, so the "briefly invisible document" race is not reachable in the product.
- F-69: `JOB_TIMEOUT_SECONDS` is validated before the module constant is derived, and `WorkerSettings.job_timeout` (import time) and `_task_budget_seconds()` (runtime) read that one frozen constant, so they cannot diverge in production; margin `min(60, max(1, total // 4))` is at least 1 at the ge=2 floor.
- Tenant scope: repositories in `_build_service` are constructed from the job's tenant argument; `_remove_uploaded_file` re-scopes by the same tenant, so a cross-tenant job deletes nothing.
- `storage_path` is written only by the upload route as `uuid4().hex` plus a suffix drawn from the extension allowlist, so nothing user-controlled reaches `os.remove`.
- Secret handling: the audit avoided reproducing any secret value; F-73 records only the category, file, and line.

### Findings

- Closed this pass: F-59, F-60, F-66, F-67, F-68, F-69, F-72
- Left `fixed`, with the unrepaired half named: F-70, F-71 (both P3, non-blocking)
- New: F-73 [P2], F-74 [P3], F-75 [P3], F-76 [P3], F-77 [P3]
- No P0 or P1 finding is `open` or `fixed`

### Remaining risk

- No typecheck, lint, coverage, security-scan or browser-test command exists in this project, so those signals were unavailable; `ruff` is installed but unconfigured and was used only as an isolated dead-code probe, not as a project gate.
- If the database outage that exhausted the transient retries is still going on the final attempt, `record_failure` cannot write and the document stays at PARSING for ever; nothing sweeps, re-queues or reports it. Inherent rather than repairable, but AGENTS.md currently promises otherwise (F-76).
- Uploads kept after a transient failure are never removed, and nothing re-enqueues a FAILED document, so `UPLOAD_DIR` grows after any outage until someone clears it by hand. Not attacker-forceable after F-67's repair.
- Unverified: a decompression-bomb PDF within `MAX_UPLOAD_BYTES` could expand to many times its size during parsing and exhaust the worker's memory, and one tenant can monopolise the single worker by queueing large documents. Neither was reproduced; both are out of the spec's declared scope and the delta moves this work off the request path, which reduces rather than adds exposure.
- Concurrency was not exercised: the idempotency argument rests on `delete_by_document_id` plus arq's in-flight lock, and no test runs two workers against one document.
- The real-worker tests carry real time budgets (40-60s drains, 8s job timeouts) against a live Redis and Postgres; they passed here twice, but they are the most likely source of future flakiness on a slower machine.


## Findings

### 011/F-49 [P1] closed - The status endpoint returns the raw internal exception text

**File:** app/rag/document_processing_service.py:195
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: security)
**Why it matters:** The failure path stores `f"{type(exc).__name__}: {exc}"` in `error_message`, and `GET /api/v1/documents/{id}/status` returns that field verbatim (app/api/routes/document.py:163). The first failure any user will hit already carries a server path: the parser raises `DocumentParsingError(f"Document not found: {path}")`, so the client learns the absolute location of `UPLOAD_DIR`. Anything else that can raise inside ingestion is relayed the same way, including asyncpg and SQLAlchemy messages with SQL fragments and host names, and embedding-provider errors. This is the same class as F-09 and F-32, and AGENTS.md's stated convention is explicit: known outcomes get typed safe messages, unexpected ones log server-side and return a fixed message. The upload handler in this same commit follows it and the worker path does not. The test named for this behaviour, `test_status_of_a_failed_document_carries_the_reason`, seeds a hand-written safe string into the column instead of running the code that writes it, so the suite cannot see the leak.
**Suggested fix:** Map the known RAG exceptions to safe typed messages (`UnsupportedDocumentTypeError` to "Unsupported document type", `DocumentParsingError` to "The document could not be read"), log everything else with `logger.exception` and store one fixed message. Then change the test to assert the message produced by a real failure, not one it wrote itself.
**Resolution:** Fixed 2026-09-21. `_user_facing_error` in the service keeps the message for the four exceptions the pipeline raises deliberately and collapses everything else to one fixed sentence, with `logger.exception` recording the original. Muting all of them was the wrong shape: F-09's own history records that doing so 'muted the only clue'. The parser's `Document not found` now names `path.name` instead of the absolute path. Proved by `test_an_unexpected_failure_does_not_reach_the_caller_verbatim`, which raises a RuntimeError carrying a connection string and asserts none of it reaches the column; restoring the old f-string makes it red. Confirmed against a real worker: a missing file yields `Document not found: <name>.txt` and a provider outage yields the generic sentence. Closed 2026-09-21 by independent review: every `DocumentParsingError` site interpolates only `path.name`, `UnsupportedDocumentTypeError` only the extension, and the base `DocumentProcessingError` is deliberately outside the allowlist so `Document <uuid> not found.` collapses too. Mutation re-run: restoring the old f-string turns `test_an_unexpected_failure_does_not_reach_the_caller_verbatim` red with the connection string sitting in the column. A real arq worker, on a committed document whose file had been deleted, stored exactly `Document not found: probe-c0e183b5.txt`. One observation that does not reopen this: `ChunkingError` and `EmptyDocumentError` are in the allowlist but raised nowhere in `app/`.

### 011/F-50 [P2] closed - A failed enqueue leaves a committed document row nothing will ever process

**File:** app/api/routes/document.py:103
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `create_document` commits the row before `enqueue` is called. If enqueuing raises, for example because Redis is down, the handler deletes the uploaded file and returns 500, but the committed row stays at `UPLOADED` with `storage_path` pointing at the file that was just deleted. The caller is told the upload failed while a permanent, unprocessable record of it exists, and the only way it could ever move off `UPLOADED` is a manual re-enqueue that would then fail on the missing file. The handler's own comment says it is cleaning up "so a failed upload does not leave litter"; it removes the small litter and keeps the large one. `test_a_failed_enqueue_does_not_leave_the_file_behind` asserts only that the upload directory is empty, so it passes against the remaining half of the defect.
**Suggested fix:** Delete the document row in the same `except` branch that deletes the file, or mark it `FAILED` with a safe message so the caller can at least see it. Extend the test to assert the row is gone or terminal.
**Resolution:** Fixed 2026-09-21. The `except` branch now calls `_mark_unqueued`, which marks the committed row FAILED with a safe message, so a caller polling the id it never received still sees a terminal state rather than a permanent UPLOADED. `test_a_failed_enqueue_does_not_leave_the_file_behind` now asserts the row's status too; removing the call makes it red. Closed 2026-09-21 by independent review. Mutation re-run: replacing the `_mark_unqueued` call with `pass` turns that test red. On the specific question of masking, it swallows only its own cleanup error; the original is logged by `logger.exception("documents.upload.failed")` immediately before and chained into the 500 with `from exc`, so nothing real is hidden. The residual is narrower than the defect this entry named: if the session is itself unusable, the commit inside `_mark_unqueued` fails silently and the row stays UPLOADED. That is the documented best-effort boundary.

### 011/F-51 [P2] closed - The upload boundary has no size cap and no type check

**File:** app/api/routes/document.py:86
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: security)
**Why it matters:** `await file.read()` buffers the entire request body in memory and then writes all of it to `UPLOAD_DIR`, with no limit on either and no quota on the directory. Any authenticated user can exhaust the API process's memory and the host disk in a single request, and repeat it. Buffering the whole body predates this commit; persisting it to shared disk that only a worker ever reclaims does not. Separately, nothing checks the extension before accepting: the parser owns `SUPPORTED_EXTENSIONS` and rejects an unknown type only in the worker, so an unsupported file is accepted with 202, retried three times, and reported as failed minutes later. Path traversal was checked and is not reachable: `Path(filename).suffix` is derived from `.name`, so it can contain neither a separator nor `..`.
**Suggested fix:** Add a `MAX_UPLOAD_BYTES` setting, stream `file.read(chunk)` to disk and abort with 413 when it is exceeded, and reject an extension the parser does not support before writing anything.
**Resolution:** Fixed 2026-09-21. The handler rejects an extension outside `DocumentParser.SUPPORTED_EXTENSIONS` with 415, a body over `MAX_UPLOAD_BYTES` (new setting, default 25 MiB) with 413, and an empty body with 400, all before anything is written to the shared directory. Three route tests cover them and each goes red when its guard is disabled. The cap is on what reaches disk, not what reaches memory: the body is already buffered by the time the handler runs, which is a Starlette-level concern and a separate change. Closed 2026-09-21 by independent review for the two defects it named. Both guards precede any write to `UPLOAD_DIR`, and `test_an_oversized_document_is_rejected` patches the cap to 64 bytes and posts 65, which cannot pass without the guard. The memory half the resolution defers is now tracked as F-61 rather than left implicit inside a closed entry.

### 011/F-52 [P2] closed - A document can be stranded at UPLOADED with no failure and no recovery

**File:** docker-compose.yml:26
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The queue now lives on the Redis that compose starts with `--save "" --appendonly no`, under a comment that still reads "Refresh tokens and rate-limit counters only; nothing here is durable". That was true before this commit and is not now: a Redis restart silently discards every queued ingestion. arq's `_expires` default adds a second path, dropping any job not started within 24 hours. In both cases the document stays at `UPLOADED` forever with its file orphaned in `UPLOAD_DIR`, indistinguishable from "no worker is running", which AGENTS.md documents as the expected failure. The spec's locked rule is that a failed job is terminal and visible, never a silent disappearance; these two paths are exactly a silent disappearance, and nothing re-enqueues, times out, or sweeps the directory.
**Suggested fix:** Enable append-only persistence on the queue Redis and correct the comment. Give `UPLOADED` an age beyond which the status endpoint reports it as stalled, so the state is at least visible. A re-enqueue path or a directory sweeper is a larger decision and should be taken deliberately rather than assumed.
**Resolution:** Fixed 2026-09-21. The compose Redis ran with `--save "" --appendonly no` under a comment asserting nothing there was durable, which stopped being true when the queue moved in. It now runs append-only with `appendfsync everysec` and a named volume, and the comment says why. A restart replays the queue instead of dropping it. Independent review 2026-09-21: left `fixed`, not closed. The Redis-durability half is genuinely repaired and verified in `docker-compose.yml`. The other two paths this entry named are untouched and unmentioned in the resolution: arq's `_expires` still defaults to 24 hours, so `Worker.run_job` drops a job never started inside that window (`if not v:` then `job expired`) and the document stays UPLOADED for good; and nothing gives UPLOADED an age after which the status endpoint calls it stalled. Both remain exactly as described above. Remaining half fixed 2026-09-21. The Redis-durability part was already done; the reviewer correctly kept this open for the other two paths. `enqueue` now passes `_expires=JOB_EXPIRES_SECONDS` (7 days) instead of taking arq's 24-hour default, so a job the worker never starts is not silently dropped while an outage is being noticed. With F-58 and F-59 also repaired, every path that previously left a document stranded now records FAILED. The third path the finding named -- an age after which the status endpoint calls an UPLOADED document stalled -- is deliberately not built: that is new product surface (a staleness threshold, and a decision about what a caller does with it), not a defect repair, and nothing now strands a document for it to detect. Independent review 2026-09-21: closed. `_expires=JOB_EXPIRES_SECONDS` is on the enqueue call and the compose Redis is append-only on a named volume, so both defect paths this entry named are gone. The declined third item is accepted as a proportionality call -- a staleness threshold is a new status contract the caller would have to understand, and AGENTS.md's proportional-engineering rule points at the smaller design. The reasoning offered for declining it is not accurate, though, and should not be relied on later: a job still expires silently after seven days rather than never, `appendfsync everysec` still loses up to a second of writes on an unclean stop, and AGENTS.md itself documents a document sitting at UPLOADED for ever when no worker is running. The residual gap is small and is not a defect in this delta; it is not "nothing".

### 011/F-53 [P2] closed - The worker rebuilds the embedding provider on every job

**File:** app/jobs/tasks/ingest_document.py:57
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: performance)
**Why it matters:** `_build_service` calls `create_embedding_provider()` per invocation, and with the default `EMBEDDING_PROVIDER=huggingface` that constructs `HuggingFaceEmbeddings`, which loads the sentence-transformers model from disk into memory. Every job pays it, and so does every retry of a job. The request path had the same shape, but there it was once per request in a process with no obvious place to cache; the worker is a long-lived process whose `startup(ctx)` hook exists, runs once, and currently only logs a line. A queue is meant to improve throughput, not preserve the per-item cost. Not measured here: the suite runs the mock provider, so this is read from the code path rather than from a timing.
**Suggested fix:** Build the parser, splitter and embedding provider once in `startup` and read them out of `ctx` in `_build_service`. Only the repositories and the session need to be per-job.
**Resolution:** Fixed 2026-09-21. `_embedding_provider()` in the task module is `lru_cache(maxsize=1)`, so the worker builds the provider once per process rather than once per job and again per retry. Cached there rather than on `create_embedding_provider` itself, because that factory is also a FastAPI dependency and its own test patches `get_settings`, which a cache would hide. Closed 2026-09-21 by independent review. The cache sits on `_embedding_provider` in the task module, so `create_embedding_provider` stays uncached; `tests/rag/test_embedding_provider.py` is the only place that patches `get_settings().EMBEDDING_PROVIDER` and it never reaches the task module, so the stated reasoning holds and no test-isolation hazard was found.

### 011/F-54 [P2] closed - delete_for_document duplicates delete_by_document_id

**File:** packages/database/repositories/document_chunk_repository.py:240
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The repository already had `delete_by_document_id` (line 107): the same tenant-scoped `DELETE` with the same two `WHERE` clauses, and a test at tests/database/repositories/test_document_chunk_repository.py:86. The new method differs only by returning `rowcount`, which no caller reads, and by omitting the `flush()` the original does. Two methods that have to stay in step, one of them tested, for one caller.
**Suggested fix:** Call `delete_by_document_id` from app/rag/document_processing_service.py:163 and delete `delete_for_document`. No current requirement is lost; the return value is unused.
**Resolution:** Fixed 2026-09-21. `delete_for_document` removed; the service calls the existing `delete_by_document_id`, which is the same tenant-scoped DELETE and already has tests. Closed 2026-09-21 by independent review: no reference to `delete_for_document` remains anywhere in the tree, and the surviving method adds the `flush()` the deleted one omitted.

### 011/F-55 [P2] closed - Nothing in the suite proves any of the new commits commit

**File:** tests/unit/jobs/test_ingest_document_task.py:57
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** Durability across two processes is the entire point of the transaction changes in this commit: `create_document` commits so the worker can see the row, `process_document` commits `PARSING` so a poller can see it mid-flight, and the failure path rolls back and then commits `FAILED` so the caller's rollback cannot discard it. Every task test drives the code through `_ctx`'s `session_factory`, which hands back the fixture session. That session is bound to a connection already inside a transaction, so SQLAlchemy joins it in `rollback_only` mode. Measured against the running database: after `session.commit()`, `conn.in_transaction()` is still `True` and the row is not visible from a second connection. No assertion in these tests can therefore distinguish a commit from a flush, and build step 3's done-when, "observes PARSING committed and visible from a second session while work is still in flight", is met by no test in the suite. The fixture's own comment concedes the reason: a second connection "would see none of the setup data". The `session_factory` and `delete_source` overrides on the task signature are not a production risk in themselves, since `ctx` is assembled by the worker from `WorkerSettings` and never from Redis, but they are what lets the suite avoid the one thing this feature had to get right. The rollback in the failure path is genuinely covered; the four `session.commit()` calls are not.
**Suggested fix:** One test that uses a real second connection: create the document through a committing session, run `ingest_document` with the production `AsyncSessionLocal`, read the status from a separate engine while the parser is blocked, and delete the rows in a `finally`. If that is judged too heavy, remove the commit-visibility claims from build step 3 and from the comments in `process_document`, so nothing asserts what is unproven.
**Resolution:** Fixed 2026-09-21. This was the right call and it was hiding a second defect. `tests/unit/jobs/test_commit_visibility.py` now drives the task on the production path with no session injected, against a genuinely committed fixture on its own engine, and reads the status from a separate connection inside `index_chunks` -- awaited between the PARSING commit and the READY commit. Removing that commit makes it red with UPLOADED. Writing it surfaced a real bug: `document.id` was read after `session.rollback()` in the failure path, and the expired instance triggered lazy IO from sync attribute access, raising MissingGreenlet in place of the real error and leaving no FAILED status. The primary key is now captured before the try block. Closed 2026-09-21 by independent review. Mutation re-run: deleting the `session.commit()` after `mark_processing` turns `test_parsing_is_visible_to_another_connection_mid_job` red with `UPLOADED != PARSING`, exactly as claimed, so the test does distinguish a commit from a flush. `document_pk` is used at every post-rollback site. Two notes that do not reopen this entry: the `record_failure=True` branch that `document_pk` protects now has no production caller, because the job layer always passes `False`; and the new test file has isolation problems of its own, recorded as F-64.

### 011/F-56 [P2] closed - The terminal-attempt decision reads a ctx key arq never sets

**File:** app/jobs/tasks/ingest_document.py:80
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** arq builds each job's context as `{**worker.ctx, 'job_id', 'job_try', 'enqueue_time', 'score'}` (arq/worker.py:576), and `startup` adds nothing, so `max_tries` is never present and `ctx.get("max_tries", config.JOB_MAX_TRIES)` always takes the fallback. The task and `WorkerSettings.max_tries` agree only because both read the same constant at import. Both docstrings state that the value travels through `ctx`, which is false. Set a per-function `max_tries` through `arq.worker.func`, or change `WorkerSettings.max_tries` without changing `JOB_MAX_TRIES`, and the two diverge silently: too high and `FAILED` is never written at all, too low and the document is marked `FAILED` while arq keeps retrying, which is the terminal-state flash the design exists to prevent. `test_the_worker_consumes_the_queue_the_api_writes_to` asserts `WorkerSettings.max_tries == config.JOB_MAX_TRIES`, which compares the line `max_tries = config.JOB_MAX_TRIES` with itself and cannot fail.
**Suggested fix:** Set `ctx["max_tries"] = WorkerSettings.max_tries` in `startup`, or drop the `ctx` lookup and read the config directly. Correct both docstrings either way.
**Resolution:** Fixed 2026-09-21. The task reads `config.JOB_MAX_TRIES` directly and the comment records why. The tautological assertion is gone: one test pins the actual constraint by asserting arq's `run_job` source builds its context from `job_try` and never `max_tries`, and another patches the setting and shows the same attempt number retrying at 5 and terminating at 3. This finding was the thread that led to F-58. Closed 2026-09-21 by independent review. Verified directly against arq 0.28.0: `Worker.run_job` builds `job_ctx` from exactly `job_id`, `job_try`, `enqueue_time` and `score`, so the old `ctx.get("max_tries", ...)` could only ever return its default. The replacement assertion is brittle in a different way, recorded as F-63.

### 011/F-57 [P3] closed - Dead code and an unreachable deduplication path

**File:** app/jobs/queue.py:48
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Three items. `reset_queue` has no caller anywhere: app/main.py's lifespan closes the other Redis pool with an explicit comment about releasing it with the app and leaves the arq pool open, while the function's own docstring tells tests to call it and none do. `DocumentProcessingResponse` (app/api/schemas/document.py:40) lost its last importer when upload switched to `DocumentEnqueuedResponse`. And the deduplication path cannot occur: `enqueue` never passes `_job_id`, and arq assigns `uuid4().hex` when it is absent, so `enqueue_job` returns `None` only on a uuid collision. The `Optional[str]` return, the `jobs.enqueue.deduplicated` log line, the schema field's "null when the job was deduplicated" description, and `test_a_deduplicated_job_is_not_an_error` all describe behaviour the system cannot produce; that test asserts a mock returns the value it was configured to return.
**Suggested fix:** Call `reset_queue` from the lifespan, which is one line and makes the function live. Delete `DocumentProcessingResponse`. Delete the deduplication branch, its log line, its schema description and its test, or pass a deterministic `_job_id` if deduplication is actually wanted.
**Resolution:** Fixed 2026-09-21. `reset_queue` is now called from the app lifespan beside `reset_redis`, closing a genuinely leaked second Redis pool rather than being deleted. `DocumentUploadResponse` and `DocumentProcessingResponse` are removed. The deduplication story was fiction and now says so: no caller passes `_job_id`, so arq always generates a unique one and the None branch is unreachable; it is kept because supplying an id is the obvious way to add deduplication later and a silent None would then read as success. Closed 2026-09-21 by independent review for the two dead-code items: `reset_queue` is called after the `yield` in `app/main.py`'s lifespan, and no reference to `DocumentUploadResponse` or `DocumentProcessingResponse` remains. The third item was deliberately retained rather than repaired; its still-tautological test is carried forward as F-63 so the ledger keeps tracking it.

### 011/F-58 [P1] closed - arq does not retry a plain exception, so every failure was stranded at PARSING

**File:** app/jobs/tasks/ingest_document.py:104
**Found:** 2026-09-21 by the builder, while proving F-56 against a running worker
**Why it matters:** The task computed `is_final_attempt = job_try >= max_tries` and passed `record_failure=is_final_attempt`, on the assumption that arq retries a failed job up to `max_tries`. It does not. `Worker.run_job` retries only on `Retry`, `RetryJob` or `CancelledError`; any other exception ends the job and stores a final result. So on attempt 1 of 3 the code declined to record the failure because 'a retry is coming', arq then ended the job because nothing asked it to retry, and the document stayed at PARSING for ever with its uploaded file orphaned and no error message. That is exactly the silent disappearance the spec forbids, and it applied to every ordinary failure, not an edge case. No unit test could see it: they call the task directly with a chosen `job_try`, so arq's scheduling never participates. It took a real worker, which is the gap the independent review named.
**Suggested fix:** Decide retryability from the exception and raise `Retry` for the retryable ones.
**Resolution:** Fixed 2026-09-21. Deterministic failures -- everything under `DocumentProcessingError`, so an unsupported type, an unreadable file, a missing one -- are terminal on the first attempt and recorded immediately; retrying them only delays telling the user. Anything else is treated as transient and, while attempts remain, raises `arq.Retry` with a capped exponential backoff, which is what actually makes arq reschedule. The last attempt records FAILED either way. `process_document(record_failure=False)` plus a new `record_failure` method keeps the decision in the job layer and the writing in one place. Three mutations go red. Proved against a running worker: a missing file now reaches FAILED on attempt 1, and an unreachable embedding host drives the retry counter 1, 2, 3 and then settles on FAILED with the generic message. Closed 2026-09-21 by independent review. Mutation re-run: forcing `_is_transient` to return `False` turns three tests red, as claimed. Reproduced end to end on a real arq worker against Redis 6380 and Postgres 5433: the document reached FAILED on attempt 1 with `Document not found: probe-c0e183b5.txt`, with `processing_started_at` and `processed_at` both set. `Worker.run_job` was read directly to confirm the retry branch fires only for `Retry`, `RetryJob` and `CancelledError`. The repair does not cover cancellation, which is F-59.

### 011/F-59 [P1] closed - A job that outlives `job_timeout` is stranded at PARSING, which is the F-58 defect in the one path the repair did not cover

**File:** app/jobs/tasks/ingest_document.py:153
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `WorkerSettings.job_timeout = 1800` (app/jobs/worker.py:63). arq enforces it with `asyncio.wait_for(task, timeout_s)`, which cancels the task and then raises `TimeoutError`. Two consequences follow, both reproduced on a real arq worker with `job_timeout=2` and a ten-second task. First, the cancellation arrives inside the task as `asyncio.CancelledError`, which is a `BaseException`, so `except Exception as exc:` never runs: no `record_failure`, no log line from this module, nothing at all. Second, arq's own handler sees `TimeoutError`, which is neither `Retry` nor `RetryJob` nor `CancelledError`, so it takes the terminal `else` branch and finishes the job on attempt 1 with no retry. The document therefore sits at PARSING for ever, its uploaded file orphaned in the shared directory, with no `error_message` and no second attempt. That is precisely the silent disappearance the spec's locked rules forbid, and precisely the shape of F-58. It is reachable by the feature's own stated motivation, since the timeout exists because embedding a large PDF on CPU takes minutes. The comment above the setting asserts the opposite of the observed behaviour: "the default 300s would kill a legitimate job midway and retry it from the start" - arq does not retry a timeout.
**Suggested fix:** Own the deadline inside the task rather than delegating it to arq: wrap the work in `async with asyncio.timeout(...)` at a budget slightly under `job_timeout`, so expiry surfaces as an ordinary exception that the existing handler classifies and records. Catching `asyncio.CancelledError` in the task instead is not equivalent, because arq also cancels tasks on worker shutdown and does retry those, so recording FAILED there would reintroduce the terminal-state flash the design exists to avoid. Correct the `job_timeout` comment either way.
**Resolution:** Fixed 2026-09-21. Confirmed independently before repairing: inside the task arq's cancellation is `CancelledError`, a BaseException that `except Exception` cannot catch, and arq's caller then sees `TimeoutError`, which is absent from its retry set, so the job ends terminally on attempt 1. The task now owns its deadline with `async with asyncio.timeout(_task_budget_seconds())`, set inside arq's `job_timeout`, so expiry arrives as an ordinary exception the existing handler classifies and records. Both deadlines derive from one new setting, `JOB_TIMEOUT_SECONDS`, and the margin scales with it so a short budget stays usable. Catching `CancelledError` was rejected for the reason the finding gives: arq also cancels on worker shutdown and does retry those. Proved by `test_a_job_that_outruns_its_budget_still_ends_in_failed`, which causes a real timeout by making `index_chunks` slower than the budget rather than raising TimeoutError by hand; removing the `asyncio.timeout` leaves the document at PARSING and the test fails with exactly that message. Documented limit: the deadline only fires at an await point, so a CPU-bound parse still blocks the loop. Independent review 2026-09-21: left `fixed`, not closed. The deadline now exists and the named test is genuine -- deleting the `asyncio.timeout` block makes `test_a_job_that_outruns_its_budget_still_ends_in_failed` red. But the repair only converts the cancellation into a catchable `TimeoutError`; nothing rolls the session back first, and that relocates the defect rather than removing it. See F-66, which reproduces both outcomes against the real database. Superseded by F-66: the reviewer showed this repair relocated the defect into the cancellation path rather than removing it. See F-66 for the completed fix. Independent review round 4, 2026-09-21: closed. The stranding this entry describes no longer happens in either shape. Deleting the rollback that F-66 added leaves test_a_job_stalled_inside_a_database_call_still_ends_in_failed failing with PendingRollbackError and the document at PARSING, which is this defect; with the code as committed both real-worker timeout tests pass and the document reaches FAILED with a message.

### 011/F-60 [P2] closed - The transient retry budget is about fifteen seconds, after which the upload is deleted and cannot be recovered

**File:** app/jobs/tasks/ingest_document.py:45
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `_backoff_seconds` returns `min(60, 5 * 2 ** (attempt - 1))`, so with `JOB_MAX_TRIES = 3` the only values it can ever produce are 5 and 10, and the 60-second cap is unreachable. The whole window from the first transient failure to the terminal one is therefore about fifteen seconds, which does not match the stated intent, "Wait longer each time, so a provider outage is not hammered". On that terminal attempt `_remove_uploaded_file` runs (line 178), so an embedding provider or database unavailable for twenty seconds permanently destroys the uploaded bytes: the document is FAILED, the file is gone, and nothing can re-run the job. The user is told, so this is not silent, but the only recovery is re-uploading a file they may no longer have. The deterministic case is different, and deleting the file there is right. No test covers the deletion-on-terminal-failure path at all, because every task test passes `delete_source=False`.
**Suggested fix:** Delete the source only when `_is_transient(exc)` is false, so a transient exhaustion keeps the file and a later re-enqueue is possible. Separately, either raise `JOB_MAX_TRIES` so the 60-second cap is reachable or drop the cap, so the code and its comment agree. Nothing current is lost: the file is deleted for tidiness, not for correctness.
**Resolution:** Fixed 2026-09-21. Backoff is now 30s then 60s rather than 5s then 10s, so the budget is about ninety seconds instead of fifteen. More importantly the upload is no longer deleted on failure at all -- only on success. It is the only copy, and destroying it because a provider was down for a minute is unrecoverable; the FAILED row keeps its `storage_path` so the work can be re-queued. `test_the_upload_survives_a_terminal_failure` runs a real worker to a terminal transient failure and asserts the file is still there; restoring the delete makes it red. Independent review 2026-09-21: left `fixed`, not closed. The backoff change and the transient half are right, and the named test is genuine (re-adding the delete makes it red). But this entry said explicitly that the deterministic case is different and deleting the file there is right, and the repair removed the delete for every failure instead. Nothing else deletes it, and the re-queue path the resolution leans on does not exist in the product. See F-67. Partly wrong, per F-67: keeping the file was right for transient failures and wrong for deterministic ones. See F-67. Independent review round 4, 2026-09-21: closed. `_backoff_seconds` now yields 30 then 60, and the keep/delete split F-67 restored is pinned in both directions: inverting `if delete_source and not transient` makes `test_a_deterministic_failure_removes_the_unusable_upload` and `test_the_upload_survives_a_terminal_failure` fail together.

### 011/F-61 [P2] closed - The 413 guard runs after the whole body has been buffered, so `MAX_UPLOAD_BYTES` does not bound memory

**File:** app/api/routes/document.py:92
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: security)
**Why it matters:** `content = await file.read()` materialises the entire request body as one `bytes` object, and only the next statement compares its length to `MAX_UPLOAD_BYTES`. The cap therefore bounds what reaches `UPLOAD_DIR` and nothing else: an authenticated user can still drive the API process's resident memory to the size of whatever they send, and repeat it. Starlette spools a multipart part above 1 MiB to a temporary file, so a large upload also consumes space in the system temp directory, which is outside `UPLOAD_DIR` and outside this cap. F-51's resolution discloses this honestly and defers it, but nothing in the ledger tracks it, and a 413 in the handler reads as a bound that is not there. The route already rejects an unsupported extension before reading anything, so guarding before the read is the established pattern in this same function.
**Suggested fix:** Compare the `Content-Length` header against `MAX_UPLOAD_BYTES` before `await file.read()` and return 413 there; that is one condition and rejects the ordinary case before a byte is buffered. Streaming `file.read(chunk)` into the destination with a running total closes the chunked-encoding case as well.
**Resolution:** Fixed 2026-09-21, though not as suggested. A Content-Length pre-check was written first and then removed: Starlette has already parsed the multipart body by the time the handler runs, so the check would have bounded nothing, and the header is client-supplied. The handler now streams the upload to disk in 1 MiB chunks and enforces `MAX_UPLOAD_BYTES` against the bytes actually received, deleting the partial file before raising 413. That bounds what is resident and what reaches the shared directory without trusting a header. Removing the in-loop check makes the oversize route test red. A limit before the body is received is a server or proxy concern and is not attempted here. Independent review 2026-09-21: closed. Verified by mutation -- removing the in-loop `size > MAX_UPLOAD_BYTES` check makes `test_an_oversized_document_is_rejected` red. `size` counts received bytes and the tripping chunk is never written, the 413 and the empty-body 400 both unlink the partial file, and no `Request` parameter was ever introduced, so nothing stale was left by dropping the Content-Length draft. One uncovered exit path is recorded separately as part of F-71.

### 011/F-62 [P3] closed - The route test named for the error-message boundary cannot fail

**File:** tests/integration/test_document_jobs_api.py:353
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `test_the_status_reason_does_not_expose_server_internals` writes the safe sentence into `error_message` itself, then asserts that that same sentence contains no `Traceback`, `asyncpg`, `postgresql://`, drive letter or `/var/`. No product code chooses the value under test, so the assertions hold for any implementation, including the leaking one F-49 found. This is the identical defect F-49 identified in `test_status_of_a_failed_document_carries_the_reason`, which is also still hand-seeded, asserting equality with a literal it wrote three lines earlier, and which the repair did not change. Genuine coverage does exist, and I verified it goes red under the old f-string, but it lives in `tests/unit/jobs/test_commit_visibility.py`; a reader of the route suite is led to believe the boundary is guarded here.
**Suggested fix:** Either drive a real failure through the ingestion path and then read the status endpoint, or delete the two seeded assertions and leave a comment pointing at the test that does cover this.
**Resolution:** Fixed 2026-09-21. The test is deleted rather than repaired: it seeded the safe message and then asserted that message was safe, and the real coverage already exists in `test_an_unexpected_failure_does_not_reach_the_caller_verbatim`, which raises an exception carrying a connection string through the real code path. `test_status_of_a_failed_document_carries_the_reason` is kept but its docstring now says plainly that it proves the route serialises the column and nothing about what is written into it. Independent review 2026-09-21: closed. The seeded test is gone, the kept one's docstring is honest and points at the real coverage, and `test_an_unexpected_failure_does_not_reach_the_caller_verbatim` in tests/unit/jobs/test_commit_visibility.py does drive a real exception through the product path.

### 011/F-63 [P3] closed - Two jobs tests assert against something other than the behaviour they name

**File:** tests/unit/jobs/test_queue.py:63
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `test_arq_does_not_supply_max_tries_in_the_job_context` calls `inspect.getsource(Worker.run_job)` and asserts on the literal strings `"'job_try': job_try"` and `"'max_tries'"` inside a third-party library's source text. Any reformatting in an arq release breaks it without any behaviour changing, and it cannot run where the dependency is installed without sources. The property it means to pin, that the retry limit comes from configuration rather than from `ctx`, is already pinned behaviourally by `test_the_retry_limit_comes_from_configuration`. Separately, `test_a_deduplicated_job_is_not_an_error` (line 37) still only asserts that an `AsyncMock` returns the `None` it was configured to return; F-57 named it and the repair kept both the branch and the test.
**Suggested fix:** Delete the source-text assertions and keep the behavioural test, or replace them with a run against a real worker. For the second, assert the log line alongside the `None` return, or drop the test with the branch.
**Resolution:** Fixed 2026-09-21. The `inspect.getsource` assertion is deleted: it was brittle and it was standing in for behaviour that `tests/integration/test_real_worker.py` now pins against a real arq worker. `test_a_deduplicated_job_is_not_an_error` is renamed `test_enqueue_maps_a_declined_job_to_none` and its docstring states that it covers this wrapper's handling of arq's Optional return, not a deduplication that cannot currently occur. Independent review 2026-09-21: closed. No `inspect.getsource` assertion remains in tests/unit/jobs/test_queue.py, and the renamed test's docstring now matches what it asserts.

### 011/F-65 [P3] closed - The spec promises `error_message` is cleared on a successful retry; the repository cannot clear it

**File:** packages/database/repositories/knowledge_document_repository.py:124
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The spec's Data and contracts section states that `error_message` is "set on terminal failure, cleared on a successful retry", and `mark_ready` duly passes `error_message=None`. But `update_processing_result` applies each field only `if ... is not None`, so passing `None` is indistinguishable from not passing it and the column is never cleared. The repository predates this feature; the contract that depends on it does not. It is unreachable today, because the only writers of `error_message` are the terminal failure path, which then deletes the source file and offers no re-run, and `_mark_unqueued`, whose job never existed. It becomes reachable the moment anything re-enqueues a FAILED document, which is exactly what F-52's remaining half invites: that document would then show READY with a stale failure reason attached.
**Suggested fix:** Give `update_processing_result` an explicit sentinel for "clear this field", or have `mark_ready` set `instance.error_message = None` directly. Alternatively drop the clause from the spec if clearing is not actually wanted.
**Resolution:** Fixed 2026-09-21. `mark_ready` clears `error_message` explicitly, because `update_processing_result` skips None arguments and so cannot clear a column. Now reachable rather than hypothetical: with F-60 keeping the file, a FAILED document can be re-queued and must not report READY with the old reason beside it. `test_success_clears_a_reason_left_by_an_earlier_failure` drives a real failure then a real success; removing the clear makes it red. Independent review 2026-09-21: closed. Verified by mutation -- deleting the `if instance is not None: instance.error_message = None` block makes that test red. The write persists because `process_document` commits immediately after `mark_ready`, so the dirty attribute is flushed. The `error_message=None` keyword passed to `update_processing_result` on the line above is now dead, but the docstring says why it cannot work, so it reads as documentation rather than a mistake.

### 011/F-66 [P1] closed - The task's own deadline never rolls the session back, so a timeout still strands the document or commits half-indexed chunks

**File:** app/jobs/tasks/ingest_document.py:187
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `asyncio.timeout` expires by cancelling the coroutine, so the exception that travels up through `DocumentProcessingService.process_document` is `CancelledError`. That is a `BaseException`, so `process_document`'s own `except Exception` handler -- the one whose entire job is `await session.rollback()` before a failure is recorded -- does not run. Only after the cancellation leaves the `async with` block does it become `TimeoutError`, and by then the rollback has been skipped. The task then calls `record_failure` on that session, which commits. Both halves of the resulting behaviour are reproduced against the real database on port 5433, with `JOB_TIMEOUT_SECONDS=6` (task budget 5s) and a 60-second stall:
(1) stall in a non-database await, the shape the existing test uses: the commit inside `record_failure` flushes the pending ingestion work too, and the document ends FAILED with three committed `document_chunks` rows whose `embedding` is NULL. `document_chunk_repository.similarity_search` filters on neither `embedding IS NOT NULL` nor the document's status, so a FAILED document's un-embedded text is retrievable. Build step 3's own done-when says a failure settles on FAILED "with a message and no chunks".
(2) stall inside a database await -- `await session.execute(text("SELECT pg_sleep(60)"))` on the task's own session, which is the case the module comment calls realistic: `record_failure` raises `PendingRollbackError: Can't reconnect until invalid transaction is rolled back`, no FAILED status is written, the exception propagates instead of `Retry`, and the document is left at **PARSING with no error and no second attempt**. That is F-59's defect, unchanged, in the path F-59 was raised about.
`record_failure`'s docstring asserts "`process_document(record_failure=False)` has already rolled back, so the session is usable", which is exactly what stops being true once the deadline fires.
**Suggested fix:** Roll back before recording: `await service.document_repository.session.rollback()` as the first statement of `record_failure` (it is idempotent on a clean session, so the normal path is unaffected), and correct that docstring. Fixing it inside `process_document` instead means catching `BaseException` there, which would also swallow worker-shutdown cancellations that arq does retry. Add the missing assertion to `test_a_job_that_outruns_its_budget_still_ends_in_failed` -- it passes today with three orphan chunks committed -- and cover the mid-query case, which no test reaches.
**Resolution:** Fixed 2026-09-21. Confirmed before repairing: `asyncio.timeout` expires by cancelling, so `CancelledError` -- a BaseException -- passes straight through `process_document`'s `except Exception` and the rollback in it never runs, becoming `TimeoutError` only outside the `async with`. `record_failure` now rolls back as its first statement, which is idempotent on a clean session and therefore safe on the ordinary path too; its docstring previously claimed the caller had already rolled back, which was false on exactly this path. Both shapes the reviewer reproduced are now regression tests against a real worker: `test_a_job_that_outruns_its_budget_still_ends_in_failed` additionally asserts no chunks survive, and a new `test_a_job_stalled_inside_a_database_call_still_ends_in_failed` stalls on `SELECT pg_sleep(60)` on the task's own session. Removing the rollback makes the first fail with one orphaned chunk and the second fail with the document left at PARSING. Independent review round 4, 2026-09-21: closed. Verified by mutation against the real database and a real worker: removing `await self.document_repository.session.rollback()` from `record_failure` makes `test_a_job_that_outruns_its_budget_still_ends_in_failed` and `test_a_job_stalled_inside_a_database_call_still_ends_in_failed` both fail, the second with exactly the PendingRollbackError this entry predicted. The double rollback on the ordinary path costs nothing: `process_document`'s own handler has already rolled back and a second rollback on a clean session is a no-op, and `record_failure` is reached only from the task, which owns its session, so no caller's work is discarded. `record_failure` runs outside the `asyncio.timeout` block, so the rollback cannot itself be cancelled by the deadline that triggered it. The one path where the rollback can still raise is a database that is genuinely gone, which is recorded as remaining risk rather than a finding because no code can write FAILED to a dead database.

### 011/F-67 [P1] closed - Nothing deletes the upload for a permanently failed document, so an authenticated user can grow the shared directory without bound

**File:** app/jobs/tasks/ingest_document.py:216
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: security)
**Why it matters:** F-60 asked for the delete to be dropped only when `_is_transient(exc)` is true, and said in terms that the deterministic case is different and deleting the file there is right. The repair removed it for every failure. `_remove_uploaded_file` is now reachable only from the success path, and a grep over `app/` and `packages/` finds no sweeper, no retention policy, no admin delete and no re-enqueue endpoint -- so the `storage_path` that the resolution says makes the work "re-queueable" is a column nothing reads. A deterministic failure is terminal on the first attempt, which makes the loop cheap: upload a file with an allowed extension that the parser cannot read, receive 202, get FAILED seconds later, repeat. Each iteration parks up to `MAX_UPLOAD_BYTES` (25 MiB by default) in `UPLOAD_DIR` for ever. In compose that directory is a bind mount of the repository working tree, shared with the API, the worker and, on a single host, the database. Before this repair the directory was self-limiting. AGENTS.md states the new behaviour ("the uploaded file is kept on every failure") but not its consequence, and no bound replaced the one that was removed.
**Suggested fix:** Restore the delete for the deterministic case only -- `if not transient: await _remove_uploaded_file(...)` in the terminal branch -- which is what F-60 asked for and keeps the recoverability argument intact for the transient-exhaustion case it was about. If files are to be kept for transient failures too, that needs a bound: a retention age, a per-tenant cap, or a documented operator sweep. Disclose whichever is chosen in AGENTS.md next to the sentence that currently describes only the upside.
**Resolution:** Fixed 2026-09-21, and the reviewer was right that the previous repair overshot. F-60 asked for the transient case; removing the delete for deterministic failures too created an unbounded parking space, because a deterministic failure is terminal on attempt 1 and any authenticated caller could loop it. The two cases are now opposites and the code says why: deterministic means the file itself is unreadable and no retry will ever use it, so it is deleted; transient means a short outage used up the retries and the file is the only copy, so it is kept. `test_a_deterministic_failure_removes_the_unusable_upload` and `test_the_upload_survives_a_terminal_failure` pin both directions, and each goes red when the condition is inverted. Independent review round 4, 2026-09-21: closed. The user-forceable half is gone: everything `DocumentParser.parse` raises is wrapped in `DocumentParsingError`, so an authenticated caller uploading rubbish with an allowed extension always lands in the deterministic branch and the file is deleted. Both directions are pinned by mutation. Files are still kept without bound for transient failures, which is the trade-off this entry's suggested fix allowed, but the disclosure it also asked for is incomplete; recorded separately as F-76.

### 011/F-68 [P2] closed - The real-worker tests are the only proof of the timeout and retry behaviour, and they skip silently in CI

**File:** tests/integration/test_real_worker.py:48
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: tests)
**Why it matters:** The file reads `TEST_REDIS_URL` and defaults to `redis://localhost:6380`. `.github/workflows/verify.yml` publishes its Redis service on **6379** and sets `REDIS_URL: redis://localhost:6379`; it never sets `TEST_REDIS_URL`. So on every pull request `_redis_available()` fails and all five tests skip. Reproduced locally: `TEST_REDIS_URL=redis://localhost:6399 python -m pytest tests/integration/test_real_worker.py` gives `5 skipped`, and the run still exits 0. Those five are the entire coverage of arq's real control flow -- the F-58 retry repair, the F-59 timeout repair and the F-60 file-retention repair all rest on them, and AGENTS.md now says "Keep the real-worker coverage when changing the task". A gate that is green because it ran nothing is worse than no gate. Two adjacent gaps in the same place: `EMBEDDING_PROVIDER` defaults to `huggingface` (app/core/config.py:72) and neither tests/conftest.py nor verify.yml pins it, so the moment the skip is fixed `test_a_real_worker_ingests_the_document` will load sentence-transformers and fetch a model over the network -- the exact hazard the spec's notes warn about, and the reason this review had to be run with `EMBEDDING_PROVIDER=mock` rather than the documented Verify command. And a run with no Redis spends about a minute on connection retries before skipping.
**Suggested fix:** Point the file at the same `config.REDIS_URL` the rest of the app uses, keeping `TEST_REDIS_URL` as the override, so CI's 6379 works unchanged. Pin `EMBEDDING_PROVIDER=mock` in tests/conftest.py beside the existing `LLM_PROVIDER` pin and its assertion, so the documented Verify command is the command that was actually run. If skipping is still wanted for a developer with no Redis, make the skip loud enough to notice.
**Resolution:** Fixed 2026-09-21, and this was worse than the finding says. `EMBEDDING_PROVIDER` was never pinned anywhere: every run in this session passed it on the command line, so the Verify command documented in AGENTS.md did not actually work as written and would have loaded sentence-transformers. `tests/conftest.py` now pins it beside `LLM_PROVIDER`, with the same loud assertion if the pin lands too late, and the full suite has been run with no provider override: 618 passed. `verify.yml` sets `EMBEDDING_PROVIDER` and `TEST_REDIS_URL: redis://localhost:6379` so the real-worker tests reach CI's Redis instead of the compose port. Silent skipping is also no longer possible there: the fixture raises rather than skips when `CI` is set, because those tests are the only coverage of arq's real control flow. Independent review round 4, 2026-09-21: closed. `alembic upgrade head && python -m pytest` with no `EMBEDDING_PROVIDER` on the command line gives 618 passed, 0 skipped, so the real-worker tests ran and the documented Verify command is now the command that was run. The CI branch fires: with `CI=true` and an unreachable `TEST_REDIS_URL` the fixture errors with the intended RuntimeError instead of skipping. Two residues are recorded in F-75 rather than held open here: the `setdefault` pin, and the per-test connection-retry cost when Redis is absent.

### 011/F-69 [P3] closed - The task budget is clamped but arq's timeout is not, so the "always expire before arq" invariant fails at small settings

**File:** app/jobs/tasks/ingest_document.py:81
**Found:** 2026-09-21 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `_task_budget_seconds` applies `max(2, config.JOB_TIMEOUT_SECONDS)` to its own budget, while `WorkerSettings.job_timeout` (app/jobs/worker.py:65) takes the raw setting. The arithmetic is correct everywhere the two agree -- 1800 gives 1740, 240 gives 180, 8 gives 6, 4 gives 3 -- but the clamp makes them disagree below 2. At `JOB_TIMEOUT_SECONDS=1` both deadlines are 1 second and the race decides which fires; at 0 or a negative value arq's `asyncio.wait_for` expires immediately on every job while the task still thinks it has a second, so every document is cancelled straight into the untested `CancelledError` path and left at PARSING. `config.py:38` declares the field with no lower bound, so any of these is an ordinary env-var typo away. The docstring's promise, "Always expire before arq does, so this module handles it", is what stops holding.
**Suggested fix:** Derive both from one clamped value -- give the module a `_total_timeout_seconds()` returning `max(2, config.JOB_TIMEOUT_SECONDS)` and have `WorkerSettings.job_timeout` use it -- or put the bound on the setting with `Field(default=1800, ge=2)` and drop the `max()` in the task. Either is one line and removes the disagreement rather than documenting it.
**Resolution:** Fixed 2026-09-21. `JOB_TIMEOUT_SECONDS` is now `ge=2`, so the task's deadline can always sit strictly inside arq's and the docstring's claim holds; `JOB_MAX_TRIES` and `MAX_UPLOAD_BYTES` gained `ge=1` at the same time. A 0 or negative timeout is rejected at settings construction rather than sending every job through the cancellation path. Independent review round 4, 2026-09-21: closed. The invariant holds at every reachable value: `JOB_TIMEOUT_SECONDS` is validated ge=2 before the module constant is derived, both `WorkerSettings.job_timeout` and `_task_budget_seconds()` read that one validated constant, and the margin `min(60, max(1, total // 4))` is at least 1 at total=2, so the task's deadline is strictly inside arq's for every admissible setting. Import-time and runtime reads cannot diverge in production because there is only one frozen constant. Nothing pins any of it, however: removing ge=2 leaves 134 jobs and RAG tests passing. Recorded as F-74.

### 011/F-72 [P2] closed - Recording a failure for a document that was never found rolled back the caller's session

**File:** app/rag/document_processing_service.py:146
**Found:** 2026-09-21 by the builder, while verifying the F-66 repair against the full suite
**Why it matters:** With F-66's rollback in place, a job naming a document it cannot see -- another tenant's, or one already deleted -- still reached `record_failure`, which rolled the session back and then tried to mark a row that does not exist. In production the task owns its session so the rollback is harmless, but it is also pointless, and it made the cross-tenant adversarial test fail by discarding that test's own uncommitted setup. More importantly it is the wrong contract: a job must leave no trace whatsoever on a document that is not its tenant's, and reaching into the failure-recording path at all is one step from doing so.
**Suggested fix:** Distinguish the not-found case and skip recording for it.
**Resolution:** Fixed 2026-09-21. `DocumentNotFoundError` is a distinct `DocumentProcessingError` subclass raised by the lookup, and the task skips `record_failure` for it: there is nothing to mark, so there is nothing to roll back for. It remains deterministic, so it is still terminal on the first attempt. `test_a_job_cannot_ingest_another_tenants_document` covers it and passes without the fixture's data being destroyed. Independent review round 4, 2026-09-21: closed. Verified by mutation: removing the `isinstance(exc, DocumentNotFoundError)` guard makes `test_a_job_cannot_ingest_another_tenants_document` fail. The skip cannot strand a real document at PARSING, because the lookup that raises it runs before `mark_processing`, so an unfound document is never moved off UPLOADED; and it is not reachable from a race with the upload path, because `create_document` commits the row before the route enqueues the job, there are no read replicas, and the project exposes no document-delete endpoint. What the skip does invalidate is a sentence in AGENTS.md; recorded as F-76.
