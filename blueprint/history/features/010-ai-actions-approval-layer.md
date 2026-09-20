# Feature: AI Actions & Approval Layer

**From build-plan:** feature 010
**Build attempt:** 1
**Status:** verified
**Branch:** feature/ai-actions-approval-layer

## Goal

Let the agent propose CRM-mutating actions instead of performing them, hold each
proposal as a durable record, and execute it only after a human approves. Every
transition writes to the feature 003 audit trail, so an agent-originated change
is as traceable as a human one.

Today the agent is read-only: `retrieve -> prompt -> generate -> finish`, with no
path to a write. This feature adds that path and puts a person in front of it.

## In scope

- An `AgentAction` record with a `PENDING -> APPROVED -> EXECUTED` lifecycle, plus
  `REJECTED` and `FAILED`, tenant-scoped like every other table.
- A tenant-scoped repository and a service owning the transitions.
- API endpoints to list, read, approve and reject proposals.
- Execution against a small, explicit allow-list of existing CRM service methods.
  No generic dispatcher.
- Audit entries on propose, approve, reject, execute and failure, with
  `actor_type` distinguishing the agent's proposal from the human's decision.
- A `propose` node in the agent graph that parses a structured proposal out of
  the model's answer and records it as `PENDING`.
- Tests at each layer, including an adversarial cross-tenant test.

## Out of scope

- **Native LLM tool calling.** `LLMProvider` has no `tools` parameter and the
  graph has no tool-executor node. Adding them is a larger change and is closer
  to build-plan item 023 (AI Copilot Skills). This feature uses a structured
  proposal parsed from the model's text instead, which delivers the headline
  behaviour without a provider-interface rewrite. A deliberate limitation, not
  an oversight.
- Bulk approval, delegation, or approval routing rules. One approver, one action.
- Scheduled or deferred execution. Approval executes immediately.
- Undo of an executed action. Feature 003's `before_values` makes a later
  reversal feature possible; building it now is speculative.
- Notifications of any kind.
- Rate limiting on proposals (feature 012).

## Build loop

`workflow.stepReview` is `feature`: implement all steps, then present one review
packet. `workflow.checkpointCommits` is `disabled`.

## Build steps

- [x] **1. The `AgentAction` model and migration.**
  New model in `packages/database/models/agent_action.py` with the fields under
  Data / contracts, and `AgentActionStatus` / `AgentActionType` enums in
  `packages/database/models/enums.py`. Alembic migration with
  `down_revision = "45c38c0fad33"` (the current head). Index `(tenant_id,
  status)` because listing pending actions for a tenant is the hot query.
  *Done when:* `alembic upgrade head` applies cleanly, a model test creates and
  reads a row, and `alembic downgrade -1` reverses it.

- [x] **2. `AgentActionRepository`.**
  Extend `BaseRepository` so tenant scoping comes from the base, which
  force-sets `tenant_id` on create and refuses reassignment on update. Add
  `list_pending(org_id)` ordered oldest-first.
  *Done when:* a repository test proves a second tenant cannot read or update
  the first tenant's action by id, and `list_pending` excludes decided actions.

- [x] **3. `AgentActionService` transitions, without execution.**
  `propose`, `reject`, and `approve` up to the point of dispatch. Every
  transition writes an audit entry via the existing `AuditService.log_event`,
  with `actor_type="agent"` on propose and `actor_type="user"` on the decision,
  sharing one `correlation_id` so a proposal and its outcome join up. Guard the
  transitions: only `PENDING` may be approved or rejected, and the check plus
  the status write happen in one transaction so a double-approve cannot execute
  twice.
  *Done when:* unit tests cover propose, approve, reject, approving an
  already-decided action (refused), and that each transition wrote the expected
  audit row.

- [x] **4. Execution against an explicit allow-list.**
  A module-level mapping from `AgentActionType` to one handler each, calling an
  existing CRM service method: `CREATE_TASK`, `UPDATE_TASK_STATUS`,
  `CREATE_CONTACT`, `UPDATE_CONTACT`, `UPDATE_OPPORTUNITY_STAGE`. An unknown
  type is refused, never a dynamic lookup. Validate the payload against a
  per-type Pydantic schema before dispatch. On success record `EXECUTED`, the
  resulting entity id, and an audit entry; on failure record `FAILED` with the
  error and leave the CRM unchanged.
  *Done when:* each supported type executes and produces the real CRM row; an
  unsupported type and a malformed payload are both refused before any write;
  a handler raising leaves the action `FAILED` and the database unchanged.

- [x] **5. API endpoints.**
  `GET /api/v1/actions` (pending by default, `status` filter),
  `GET /api/v1/actions/{id}`, `POST /api/v1/actions/{id}/approve`,
  `POST /api/v1/actions/{id}/reject` with an optional reason. All authenticated
  via `Depends(get_current_user)` and tenant-scoped through the service. Thin
  handlers, no business logic. Errors return safe messages and log server-side,
  following feature 009's convention.
  *Done when:* route tests execute every handler body, including approve on an
  already-approved action, a 404 for another tenant's action, and 401 without a
  token. Not a schema-only check: feature 009 shipped two endpoints that had
  never run because only the OpenAPI schema was asserted.

- [x] **6. The agent proposes.**
  A `propose` node between `generate` and `finish`. It parses an optional
  structured proposal block from the model's answer, validates it against the
  same per-type schema as step 4, and records a `PENDING` action. Malformed or
  absent proposals leave the turn unchanged; the node never blocks a normal
  answer. Add the proposal instruction to the system prompt through the existing
  prompt store from feature 008 rather than hardcoding it.
  *Done when:* a graph test shows a proposal in the model output creates exactly
  one `PENDING` action carrying the conversation id; text with no proposal
  creates none; a malformed proposal creates none and does not fail the turn.

- [x] **7. Adversarial and end-to-end coverage.**
  Add to `tests/adversarial/test_tenant_isolation.py`: tenant B cannot list,
  read, approve or reject tenant A's action. One integration test drives the
  real route from a `PENDING` action through approval to the executed CRM row
  and the audit entries.
  *Done when:* the full suite passes, and the isolation test fails if the
  service's tenant filter is removed.

## Files / areas

| Path | Change |
|---|---|
| `packages/database/models/agent_action.py` | New model |
| `packages/database/models/enums.py` | `AgentActionStatus`, `AgentActionType` |
| `alembic/versions/*_add_agent_action_table.py` | New migration from head `45c38c0fad33` |
| `packages/database/repositories/agent_action_repository.py` | New, extends `BaseRepository` |
| `app/services/agent_action_service.py` | Transitions, audit, execution dispatch |
| `app/api/routes/actions.py`, `app/api/schemas/actions.py` | New endpoints and schemas |
| `app/api/dependencies.py`, `app/main.py` | Wire the service and router |
| `app/agent/nodes/propose.py`, `app/agent/builders/graph_builder.py`, `app/agent/state.py` | The propose node |
| `tests/...` | Unit, repository, route, adversarial, integration |

## Data / contracts

**AgentAction**

- `id` (UUID, pk)
- `tenant_id` (UUID, FK tenant, indexed) - the isolation contract
- `org_id` (UUID, FK organization)
- `conversation_id` (UUID, FK conversation, nullable) - where it was proposed
- `proposed_by_user_id` (UUID, FK user) - whose turn produced it, not the approver
- `action_type` (enum `AgentActionType`)
- `payload` (JSONB) - validated against the per-type schema before execution
- `reason` (text, nullable) - the agent's stated rationale
- `status` (enum `PENDING|APPROVED|REJECTED|EXECUTED|FAILED`, default `PENDING`)
- `decided_by_user_id` (UUID, FK user, nullable), `decided_at`, `decision_reason`
- `executed_at` (nullable), `result_entity_type`, `result_entity_id` (nullable)
- `error_message` (text, nullable)
- `correlation_id` (UUID) - joins the proposal and its outcome in the audit log
- `created_at`, `updated_at`
- Index `(tenant_id, status)`

**Locked rules**

- **An action executes at most once.** The `PENDING` check and the status write
  share a transaction; a second approve is refused, not re-executed.
- **Nothing mutates the CRM before approval.** Proposing only writes an
  `AgentAction` row.
- **The approver is a real user.** `decided_by_user_id` is never the agent, and
  the audit entry for a decision carries `actor_type="user"`.
- **Unknown action types are refused.** The allow-list is a literal mapping;
  there is no dynamic attribute lookup from `payload` to a service method.
- **Tenant scope comes from the repository**, never from a value in the payload.

## Testing

`python -m pytest` with the Postgres test container
(`docker compose up -d postgres`). `tests/conftest.py` pins `LLM_PROVIDER=mock`
and asserts the pin took effect. Run the eight test directories explicitly;
`pytest tests/` as a single argument still fails to import numpy.

Baseline at spec time: 486 passed, 0 failed.

**Status: verified. 545 passed, 0 failed** across all eight directories.

Two independent review passes ran against this feature and both returned
changes-requested. The first found two P1s: a broken execution-failure path
and a cross-org boundary that filed CRM rows in the approver's org. The second
confirmed those code repairs by execution but found they had no regression
coverage at all — removing either savepoint left the whole suite green — plus a
functional gap where the proposal instruction never reached a tenant with its
own stored prompt. All are repaired; F-46 and F-48 remain open by choice.

| Area | Tests |
|---|---|
| `tests/repositories/test_agent_action_repository.py` | 5 |
| `tests/unit/services/test_agent_action_service.py` | 14 |
| `tests/integration/test_actions_routes.py` | 13 |
| `tests/agent/test_propose_node.py` | 14 |
| `tests/adversarial/test_tenant_isolation.py` | 1 added |

The isolation test was mutation-checked: removing the repository's tenant
filter makes it fail. The migration was verified by a full
upgrade/downgrade/upgrade round trip, including that both enum types are
dropped on the way down.

**Worth flagging for later:** `alembic revision --autogenerate` emitted 422
lines here. Besides this table it wanted to drop the `document_chunks` ivfflat
vector index and several foreign keys on `knowledge_documents` and `prompt` —
pre-existing drift between the models and the live schema. The migration was
therefore hand-written with only the new table. That drift is still present and
will bite the next person who runs autogenerate.

## Notes for the AI

- `BaseRepository.create` force-sets `tenant_id` and `update` pops it. Do not
  re-implement tenant filtering in the service.
- `AuditService.log_event` already accepts `actor_type` and `correlation_id`;
  feature 003 added them for exactly this use.
- `AuditAction` has no value for an approval decision. Reuse `CREATE`/`UPDATE`
  with a descriptive `entity_type` rather than widening the enum, which would
  need a migration; revisit only if the audit UI needs to filter on it.
- Follow feature 009's error convention: known outcomes get safe typed
  messages, unexpected ones log server-side and return a fixed message. Never
  return `str(exc)`.
- Route tests must execute the handler body.
- `AGENTS.md` still lists placeholder Next.js commands and there is no declared
  Verify command. `/ci` would fix that.

## Open questions

None blocking. One judgement call worth naming: **who may approve.** This spec
lets any authenticated user in the tenant approve an action proposed in their
own conversation, which matches the human-in-the-loop intent and the project's
"users within a tenant are trusted collaborators" model. Restricting approval to
a role, or forbidding self-approval, is a policy decision that needs a product
answer, and no role-dependency helper exists yet. Implemented as described;
revisit if the answer is different.

## Independent review

Two independent review passes ran against this feature (adapter `claude`, model
`claude-opus-5[1m]`, context `fresh subagent`). Neither issued a `passed`
receipt, so none is archived as passing. The honest record:

| Pass | Target | Verdict | What it found |
|---|---|---|---|
| 1 | 819d74f8 | changes-requested | Broken execution-failure path (P1), cross-org approval filing CRM rows in the approver's org (P1), 10 more |
| 2 | 5a51ce46 | changes-requested | Both P1 code repairs verified correct by execution, but with no regression coverage at all (P1); the proposal instruction never reached a tenant with a stored prompt (P2); raw blocks still reaching users (P3) |

Pass 1 reproduced both P1s end to end. Pass 2 confirmed the repairs by forcing
a genuine in-flush failure and by mutation-testing the org predicate, then
showed that removing either savepoint left the entire suite green — the fixes
were correct and completely unguarded. It also found that the test named for
the during-flush case used a payload that fails before any flush, the fourth
time in this work that a test named for a defect did not exercise it.

Everything both passes raised is repaired except F-46 and F-48, which are
recorded as open by deliberate choice. The repairs from pass 2 were not
themselves independently re-reviewed; the user elected to merge after the
second pass rather than run a third. The savepoint repairs are mutation-
verified by the builder: each of the two new tests fails with its own savepoint
removed.

Final verification: 545 passed, 0 failed across all eight test directories.

## Findings

### 10/F-37 [P1] closed - The execution failure path was itself broken

**File:** app/services/agent_action_service.py:277
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** When a handler failed inside `session.flush()`, SQLAlchemy had already rolled the transaction back, so the recovery block's own flush raised instead of running. The request returned 500, no `FAILED` status or `error_message` was written, and no audit entry was made for an agent-originated write attempt. The action silently reverted to `PENDING`, reappeared at the top of the approval queue, and failed again on every retry. Independently reproduced: approving `UPDATE_TASK_STATUS` with `{"status": "DONE"}` on a real task raised `InvalidRequestError`. `"DONE"` is the most natural status an LLM emits and is not a member of `task_status`. Two locked spec rules were false here.
**Suggested fix:** Run the handler inside a savepoint, and validate the enum values in the payload schemas.
**Resolution:** Fixed 2026-09-20. `_execute` now runs the handler inside `session.begin_nested()`, so a rollback is scoped to the savepoint and the `FAILED` write plus its audit entry still succeed. The payload schemas now type `status`, `priority` and `stage` as `Literal` mirrors of the PostgreSQL enums, so an out-of-range value is a refused proposal rather than a database error raised mid-transaction. Verified by probe: a DB-level FK violation now returns `FAILED` with an error message instead of raising. `tests/unit/services/test_agent_action_service.py` covers both failure classes separately, and the earlier test that only exercised the pre-flush path was rewritten.

### 10/F-38 [P1] closed - Cross-org approval filed the CRM row in the approver's org

**File:** packages/database/repositories/agent_action_repository.py:69
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: security)
**Why it matters:** `list_actions` filtered by `org_id`, but `get_action`, `approve` and `reject` did not. A user in org B could read and approve an action proposed in org A, and because the executors pass the approver to the CRM services, which stamp `org_id` from the current user, the created record landed in org B. The `AgentAction` row said org A, the CRM row said org B, and the two audit entries disagreed about the org. The org filter on list gave a false impression of scoping the other three operations did not honour. Independently reproduced: org B read, approved and executed org A's action, and the created task carried org B's id. This is distinct from the spec's recorded judgement call, which concerns who *within* an org may approve.
**Suggested fix:** Apply the org predicate to `claim_pending` and the read path so all four operations agree.
**Resolution:** Fixed 2026-09-20. Added `get_for_org` and an `org_id` parameter to `claim_pending`; the service uses both, so another org's action is a 404 rather than an executable row. Since approval is now same-org only, the approver's org always matches the action's and the CRM row is filed correctly. `tests/adversarial/test_tenant_isolation.py` gained a cross-org test, mutation-checked by removing the org predicate.

### 10/F-39 [P2] closed - str(exc) was returned to API clients through error_message

**File:** app/services/agent_action_service.py:286
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: security)
**Why it matters:** The routes returned fixed messages, but `AgentActionResponse.error_message` carried `f"{type(exc).__name__}: {exc}"` verbatim from both the approve response and the read endpoint, leaking internal entity ids and service wording. With F-37 repaired, SQLAlchemy and asyncpg messages containing SQL and column names would have reached clients too. The feature's own spec records the convention: never return `str(exc)`.
**Suggested fix:** Keep the detail in the log and store a short code.
**Resolution:** Fixed 2026-09-20. `error_message` now holds the exception class name only; the full detail stays in the server log. A test asserts the field contains no newlines, no SQL keywords, and stays under 100 characters.

### 10/F-40 [P2] closed - The failure test asserted nothing its name promised

**File:** tests/unit/services/test_agent_action_service.py:231
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `test_a_failing_handler_marks_failed_and_writes_no_crm_row` never queried for a CRM row, and its payload used a nonexistent `task_id`, so the handler raised before any flush — the one path where the broken recovery block happened to work. It passed against F-37. This is the "passes against the bug" pattern the spec explicitly warns about, and it is how F-37 survived the builder's own testing.
**Suggested fix:** Cover both failure classes and add the missing assertion.
**Resolution:** Fixed 2026-09-20. Split into a pre-flush case and a during-flush case, both asserting no `Task` row exists afterwards, plus a test that an out-of-range status is refused before reaching the database.

### 10/F-41 [P2] closed - The propose node was only tested against a stub echoing its own kwargs

**File:** tests/agent/test_propose_node.py:29
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** `RecordingService.propose` accepted anything and returned an object with an id, and the assertions read back the kwargs the test itself supplied. The fixture payload would have been rejected by the real `CreateTaskPayload`, so the tests would still have passed if the node and the service were incompatible. Nothing in the suite ran the compiled graph either, so spec step 6's requirement that a test observe a `PENDING` row from this path was unmet.
**Suggested fix:** One integration test with the real service asserting a single PENDING row.
**Resolution:** Fixed 2026-09-20. Two integration tests drive the real `AgentActionService`: one asserts exactly one `PENDING` row with the right `conversation_id` and payload and that the block is stripped from the response, the other asserts a payload the real schema rejects creates nothing and does not break the turn. The first one immediately caught a genuine incompatibility in its own fixture, which is the point.

### 10/F-42 [P2] closed - The propose node swallowed the exception but not the session damage

**File:** app/agent/nodes/propose.py:106
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** The node runs on the request session inside the chat turn, before the assistant message is persisted. A failure inside `propose` that reached a flush aborted the transaction; the node caught and logged it, but the later assistant-message flush then raised `PendingRollbackError` and the whole turn was rolled back. The user's answer and their own message would be lost to a 500 — exactly what the node's docstring says can never happen.
**Suggested fix:** Scope the rollback to a savepoint.
**Resolution:** Fixed 2026-09-20. `propose` wraps its write in `session.begin_nested()`. Demonstrated while building the F-41 test: a foreign-key violation inside `propose` was contained by the savepoint and the turn survived.

### 10/F-43 [P2] closed - Unused eager relationships on the hot approve path

**File:** packages/database/models/agent_action.py:149
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: performance)
**Why it matters:** `tenant` and `organization` were declared `lazy="selectin"`, adding two SELECTs to every `claim_pending`, every read and every queue listing. Neither is used anywhere: the response schema exposes only the id columns.
**Suggested fix:** Delete them.
**Resolution:** Fixed 2026-09-20. Both removed, along with the now-unused import.

### 10/F-44 [P2] closed - actor_type casing drifted from every existing audit row

**File:** app/services/agent_action_service.py:120
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Every row already in `audit_logs` carries `'USER'`, the column's server default, while this feature wrote `'user'` and `'agent'`. The first report doing `WHERE actor_type = 'USER'` — the obvious query given the stored data — would silently omit every human approval decision, which is exactly the set this feature exists to make traceable.
**Suggested fix:** Match the existing casing.
**Resolution:** Fixed 2026-09-20. Writes `'AGENT'` and `'USER'`; the assertions in three test files were updated to match.

### 10/F-45 [P3] closed - Dead exception branch in the approve route

**File:** app/api/routes/actions.py:103
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `InvalidActionPayloadError` and `UnsupportedActionTypeError` cannot escape `approve`: `_claim` never raises them and `_execute` converts them to `FAILED`. The 422 branch was unreachable.
**Suggested fix:** Delete it.
**Resolution:** Fixed 2026-09-20. Branch and its now-unused imports removed.

### 10/F-47 [P3] closed - strip_proposal could remove legitimate content or leave the block visible

**File:** app/agent/nodes/propose.py:70
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Three issues. The substitution was global with `DOTALL`, so an unterminated action fence followed by any other fence would swallow everything between them. When no factory was configured the block was not stripped, so any deployment path without it showed users raw JSON. And a reply consisting only of the block became an empty answer, which was then persisted as the assistant message. The reviewer benchmarked the pattern and confirmed it is not a ReDoS risk.
**Suggested fix:** Strip before the factory check, use `count=1`, fall back to the original text when the result is empty.
**Resolution:** Fixed 2026-09-20. All three.

### 10/F-49 [P1] closed - The during-flush failure had no real test, and a misnamed test concealed it

**File:** tests/unit/services/test_agent_action_service.py:257
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: tests)
**Why it matters:** The test named `test_a_handler_failing_during_flush_still_marks_failed` used a `CREATE_TASK` payload with a nonexistent `assigned_to_user_id`. `TaskService.create_task` resolves the assignee through a tenant-scoped repository first and raises before any flush, so the test was a duplicate of the pre-flush case and its name and docstring were false. Independently confirmed by the builder: deleting the savepoint from `_execute` left all 32 service and route tests green. The same held for the propose savepoint. Both P1 repairs from the first pass were therefore correct in code and completely unguarded — a later refactor could remove either and nothing would notice, silently restoring the original F-37 symptom. This is the fourth time in this work that a test named for a defect did not exercise it.
**Suggested fix:** Substitute a handler that writes then violates a constraint, so the failure is genuinely mid-flush, and assert the session survives.
**Resolution:** Closed 2026-09-20. Reaching an in-flush failure through the real allow-list is not possible, because every handler pre-resolves its foreign keys; the test now monkeypatches one `EXECUTORS` entry with a handler that adds a `Task` with a bad FK and flushes. It asserts `FAILED`, an error message, no CRM row, three audit rows ending in the failure, and that a subsequent `propose` still works. A second test calls `propose` with a nonexistent `conversation_id` and asserts a later flush on the same session succeeds. Both mutation-verified: removing the `_execute` savepoint fails the first, removing the `propose` savepoint fails the second.

### 10/F-50 [P2] closed - The proposal instruction never reached an org with a stored prompt

**File:** app/agent/nodes/prompt.py:26
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** `prompt_node` prefers a prompt from the feature-008 store and falls back to the built-in one only when the store returns None. The whole proposal instruction had been added to the fallback, so any org with its own `crm_chat` prompt got a system prompt that never mentioned the action block: the model never emitted one and the entire approval layer was silently inert for that tenant, with no error and no log line. The spec's step 6 said explicitly to route this through the prompt store rather than hardcoding it.
**Suggested fix:** Append the instruction to whatever the store returns, keeping one source of the text.
**Resolution:** Closed 2026-09-20. The instruction is now `ACTION_PROPOSAL_INSTRUCTION`, a separate constant. `get_system_prompt()` appends it to the built-in prompt, and `prompt_node` appends it to a stored prompt that does not already contain it, so there is one source and no duplication. `tests/agent/test_prompt_node_proposal_instruction.py` (3 tests) covers the stored-prompt case, the fallback case, and non-duplication.

### 10/F-51 [P3] closed - Raw action blocks still reached users on three paths

**File:** app/agent/nodes/propose.py:110
**Found:** 2026-09-20 by /audit independent current (scope: current; lens: quality)
**Why it matters:** Stripping was driven by successful parsing, so a block whose JSON was malformed was returned to the user verbatim — and malformed JSON is the commonest way a model gets this wrong. A test asserted that behaviour as correct. Two other paths leaked as well: `count=1` left a second block, and a reply consisting only of a block fell back to returning the raw block. In each case `ChatService` streams that text and persists it, so the JSON becomes permanent in the conversation.
**Suggested fix:** Strip on a body-agnostic fence pattern, globally, and replace a block-only reply with a sentence.
**Resolution:** Closed 2026-09-20. Added `_ANY_PROPOSAL_FENCE`, which matches an action fence whether or not its body parses, applied globally. A block-only reply now yields a short sentence pointing at the pending actions list rather than raw JSON or an empty message. The original response is kept in state so extraction still works after stripping. All four cases verified directly, and the test that asserted the old behaviour was corrected.
