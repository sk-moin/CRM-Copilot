# Feature: Rate Limiting

**From build-plan:** feature 012
**Build attempt:** 1
**Branch:** feature/rate-limiting
**Status:** verified

## Goal

Put a per-tenant and per-user ceiling on request volume, so one tenant cannot
exhaust the shared database, Redis, worker or LLM budget for everyone else, and
so an unauthenticated caller cannot sit on `/auth/login` guessing passwords.

Nothing in the API limits anything today. Every route is unmetered, including
`POST /auth/login`, which is now backed by real bcrypt, and the chat and RAG
routes, where one request costs a Groq call and an embedding pass.

## In scope

- `fastapi-limiter` initialised against the Redis this project already runs,
  released with the app like the other two pools.
- An identifier derived from the authenticated user, falling back to the client
  address when there is no user yet.
- Three tiers, because the cost per request genuinely differs: strict on the
  unauthenticated auth routes, strict on the AI routes that spend money, and
  generous on ordinary CRM reads and writes.
- A `429` that tells the caller when to come back.
- Defined behaviour when Redis is unreachable.
- Limits as configuration, not literals in route decorators.
- Tests, including an adversarial one for the identifier.

## Out of scope

- Per-plan or per-subscription quotas. That is feature 019 (Billing & Quotas);
  this feature meters requests, it does not price them.
- Any quota on the worker. Jobs do not arrive over HTTP, and the enqueueing
  route is already limited by this feature.
- A dashboard, metrics or alerting for throttling. Feature 013 owns
  observability; this feature logs and nothing more.
- Distributed fairness or token-bucket smoothing. A fixed window per tier is
  the smallest thing that meets the requirement.

## Decisions

Three choices the plan does not make, taken here with reasons rather than left
open, because each is reversible and none changes the data model.

**Identifier source.** The bucket key comes from the same signed JWT
`get_current_user` trusts, never from a request header. A header-derived
identity would let any caller pick their own bucket and make the whole feature
decorative. It is decoded directly rather than by calling `get_current_user`
itself: the identifier runs on every request, including ones that end up
rate-limited before reaching the route, and that dependency does a database
lookup on top of the JWT decode -- a cost this shortcut avoids while keeping
the same trust boundary (a validated signature), since the two token halves
that matter, `sub` and `tenant_id`, are already in the verified payload.
For anonymous routes the key is the client address.

**Client address behind a proxy.** `X-Forwarded-For` is client-supplied and
trivially spoofed, so honouring it by default would reopen the same hole. The
direct peer address is used unless `TRUSTED_PROXY_COUNT` is set above zero, in
which case that many entries are trimmed from the right of the chain. Render
and Vercel both put exactly one proxy in front, so this is a deployment
setting, not a guess baked into code.

**Redis unreachable.** Fail open, and log a warning. A rate limiter that takes
the whole API down when its counter store blinks converts a minor dependency
outage into a total one, and this project already treats Redis as the place for
things that can be rebuilt. The trade is stated in `AGENTS.md`: while Redis is
down, nothing is throttled.

## Build loop

`workflow.stepReview` is `feature`, so the steps below are built in order and
reviewed as one packet at the end. `workflow.checkpointCommits` is `disabled`,
so no per-step commits; `/complete` makes the single work commit.

## Build steps

- [x] **1. Dependency, settings and lifespan.**
  Add `fastapi-limiter` to `requirements.txt`. Initialise it in `app/main.py`'s
  lifespan from the existing `get_redis()` client rather than a fourth
  connection, and close it beside `reset_redis` and `reset_queue`. Add the
  tier limits and `TRUSTED_PROXY_COUNT` to `app/core/config.py` with `ge=`
  bounds, following the settings validation added for feature 011.
  *Done when:* the app starts and `GET /health` still answers, a unit test
  asserts the limiter is initialised with the project's Redis and shut down
  with the app, and out-of-range limit values are refused at settings
  construction.

- [x] **2. The identifier, and an adversarial test for it.**
  A callable returning `tenant:<id>:user:<id>` for an authenticated request and
  `ip:<addr>` otherwise, reading the user from the same dependency the routes
  use. Client address per the decision above.
  *Done when:* two users in one tenant get separate buckets, the same user gets
  one bucket across two routes in the same tier, and a request carrying a
  forged `X-Forwarded-For` lands in the same bucket as one without it while
  `TRUSTED_PROXY_COUNT` is zero.

- [x] **3. The 429 contract.**
  A limited request returns `429` with a `Retry-After` header in seconds and a
  JSON body matching the shape the rest of the API returns errors in. The
  message says what to do and names no internal detail, following the rule
  feature 011 established for `error_message`.
  *Done when:* a route test drives a tier over its limit and asserts the
  status, the header, and that the body carries no bucket key, Redis detail or
  internal identifier.

- [x] **4. Apply the tiers.**
  Strict on `POST /auth/login` and `POST /auth/register`, keyed by address.
  Strict on the AI routes (`/chat/stream`, the RAG query route, and document
  upload, which enqueues work). Generous on the remaining CRM routes. Applied
  as router-level dependencies, not repeated per handler.
  *Done when:* one over-limit test per tier passes, a route in the generous
  tier is unaffected by exhausting the strict tier, and no route is limited
  twice.

- [x] **5. Redis unreachable.**
  Requests succeed and a warning is logged once per outage window rather than
  per request.
  *Done when:* a test points the limiter at an unreachable Redis and shows a
  normal `200` plus one warning, not a `500` and not silence.

- [x] **6. Documentation.**
  The tiers, the settings, the proxy note and the fail-open trade recorded in
  `AGENTS.md` under a heading beside the background worker section.
  *Done when:* every claim in that section is one the code keeps, checked the
  way feature 011's F-76 was.

- [x] **7. Keep completed ingestion idempotent on worker redelivery (F-90).**
  A worker can commit READY and remove the upload, then crash before arq
  acknowledges the job. A redelivery must return the existing READY result
  without resetting the document to PARSING or trying to parse the removed
  file.
  *Done when:* a regression test completes ingestion with source deletion,
  runs the same task again, and confirms the document remains READY with its
  chunks intact and no second parse attempt.

- [x] **8. Keep auth-tier buckets keyed by client address (F-91).**
  Login and registration must share one auth-tier allowance per client
  address even when the request carries a valid bearer token. AI and default
  tiers remain keyed by signed tenant/user identity.
  *Done when:* an auth-tier request with a valid bearer token is observed using
  an `ip:<address>` Redis key, while the normal identifier still uses the
  tenant/user key for that same request.

## Files / areas

- `app/core/config.py` - tier limits, `TRUSTED_PROXY_COUNT`
- `app/main.py` - lifespan init and shutdown
- `app/api/rate_limit.py` (new) - identifier, tier dependencies, 429 handler
- `app/api/routes/auth.py`, `chat.py`, `rag.py`, `document.py`, and the CRM
  routers in `app/main.py` - tier application
- `app/rag/document_processing_service.py` - return the committed READY result
  on redelivery
- `requirements.txt`, `AGENTS.md`
- `tests/unit/api/test_rate_limit.py`, `tests/integration/test_rate_limit_routes.py`,
  `tests/adversarial/test_rate_limit_identifier.py` (new)
- `app/api/rate_limit.py` - auth-specific client-address identifier
- `tests/unit/api/test_rate_limit.py` - assert the actual auth-tier Redis key
- `tests/unit/jobs/test_ingest_document_task.py` - redelivery regression

## Data / contracts

Nothing persisted, no migration. Counters live in Redis under a
`fastapi-limiter` prefix and expire with their window.

`429` response:

```json
{ "detail": "Too many requests. Retry in 37 seconds." }
```

with `Retry-After: 37`. The identifier never appears in a response.

## Testing

`python -m pytest`, with the existing Postgres on 5433 and Redis on 6380. The
limiter tests use a distinct Redis key prefix so they cannot collide with the
job queue or with a developer's running app, and they reset their keys in
teardown the way `test_real_worker.py` does.

## Notes for the AI

Mutation-test every limit and every guard: revert the change, confirm the named
test goes red. Five tests across feature 011 passed against the defect they
were named for, and the pattern was always the same -- an input chosen so that
the guard and its absence produced the same result.

Two specific traps for this feature. A test that exhausts a limit and then
asserts `429` will pass even if the limiter is keyed on something wrong, so the
identifier needs its own test showing two principals do not share a bucket.
And a fixed window means the counter resets on a boundary, so a test that
sends `limit + 1` requests can flake if it straddles one; pin the window rather
than sleeping through it.


<!-- blueprint:completion {"schemaVersion":1,"specBytes":9489,"specSha256":"8dfeff0961bf02766871754cddf03fc9be712125bed89783e56411eb91b853fb","branch":"refs/heads/feature/rate-limiting","head":"923caf1f117d5ffdc472d276d0d8b5aad73aeac6","baseRef":"refs/heads/main","baseCommit":"a3cbdb82646371413c604d234ff0d8323cff51b8","sourceTree":"38cbb4629e7558352c1b263d9edfa2efb058d319","absentOptional":[]} -->

## Independent review

# Independent Review

**Status:** passed
**Target commit:** 923caf1f117d5ffdc472d276d0d8b5aad73aeac6
**Base commit:** a3cbdb82646371413c604d234ff0d8323cff51b8
**Base ref:** main
**Spec hash:** 8dfeff0961bf02766871754cddf03fc9be712125bed89783e56411eb91b853fb
**Prepared by:** copilot
**Builder model:** unknown (runtime did not expose exact model)
**Requested reviewer:** copilot
**Requested model:** runtime default (exact model not known until reviewer starts)
**Requested execution:** automatic
**Requested at:** 2026-09-29T19:59:20+05:30
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** copilot
**Reviewer model:** unknown (runtime did not expose exact model)
**Reviewer context:** fresh session
**Actual execution:** manual
**Reviewed at:** 2026-09-29T20:00:19+05:30
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

## Commands

- `python -m pytest tests/unit/api/test_rate_limit.py tests/integration/test_rate_limit_routes.py tests/adversarial/test_rate_limit_identifier.py tests/unit/jobs/test_ingest_document_task.py tests/rag/test_document_processing_service.py -q`: pass

## Evidence

- Reviewed the complete `a3cbdb8..923caf1` delta for rate limiting, including `app/api/rate_limit.py`, `app/core/config.py`, `app/main.py`, and the focused regression tests.
- Confirmed the implementation uses one shared budget per tier and per identifier, applies the auth/AI/default tiers correctly, fails open with a single warning when Redis is unreachable, and preserves READY ingestion on redelivery.
- Targeted verification passed in the local Postgres/Redis stack: the selected suite completed successfully with no failing assertions.

## Findings

- None

## Remaining risk

- None identified


## Findings

- None
