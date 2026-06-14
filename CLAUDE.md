# CLAUDE.md — Project Constitution

This file is read automatically at the start of every Claude Code session.
It is the highest-priority instruction set. If anything in a spec conflicts
with this file, STOP and ask before proceeding.

## Project

CRM Copilot — multi-tenant CRM with an AI agent (tool-calling, RAG-augmented)
built on a ₹0/month free-tier stack. See `docs/architecture.md` for the
full picture and `specs/` for per-module specifications.

## How we work together (READ THIS FIRST)

1. **Spec-driven.** Every feature has a corresponding file in `specs/`.
   Implement to the spec. If the spec is ambiguous or missing something
   you need, STOP and ask — do not assume and proceed.

2. **Plan before code.** For any new spec, first produce an implementation
   plan (files to create/modify, order, key decisions) WITHOUT writing code.
   Wait for explicit approval ("proceed" / "go ahead") before writing files.

3. **Small diffs.** One spec = one session = one reviewable diff. Do not
   sprawl across unrelated modules in the same session. If you discover
   a change needed in another module, note it and ask — don't just do it.

4. **No autonomous git operations.** Never run `git commit`, `git push`,
   `git checkout -b` on remote branches, or `git reset --hard` without
   explicit confirmation for that specific command. I review and commit.

5. **No new dependencies without listing them first.** Before adding any
   package to requirements.txt / package.json, tell me the name, version,
   and why. Wait for approval.

6. **No destructive DB operations.** Never run `alembic downgrade`,
   `DROP TABLE`, or any command against a non-local database without
   explicit confirmation. Local dev DB only, and say so when you do.

7. **Summarize after each file.** After writing or editing a file, give a
   short summary of what changed and why before moving to the next file.

8. **Surface tradeoffs, don't hide them.** If you make a judgment call
   (e.g., choosing a library, an index type, an error-handling strategy),
   say so explicitly so I can override it. Don't silently pick the
   "easiest" option and move on.
9. **Never fabricate command output.** If you cannot run a command (e.g., due to sandbox limits, Docker or DB inaccessibility), state that explicitly. Do not invent placeholder output like `X.XXs` or simulated results. Real test output only – if you cannot run it, say so and I’ll run it myself.

## Tech stack (do not substitute without asking)

- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.x (async), Alembic
- **Database**: PostgreSQL (Neon free tier) + pgvector extension
- **Cache**: Redis (Upstash/Redis Cloud free tier) — session, rate limiting,
  short-term memory ONLY. Never durable storage.
- **Frontend**: Next.js 15 (App Router), TypeScript, TanStack Query
- **AI**: OpenRouter (OpenAI-compatible API), config-driven model routing
  via `config/models.yaml`
- **Embeddings**: Local — `BAAI/bge-small-en-v1.5` via sentence-transformers
- **Auth**: JWT + refresh tokens, RBAC via role claim
- **Rate limiting**: `fastapi-limiter` (Redis-backed)
- **Testing**: pytest (backend), vitest (frontend)

## Hard architectural rules

- **Tenant isolation is non-negotiable.** Every table that holds tenant data
  has a `tenant_id` (or reaches it via `organization_id`). Every repository
  query MUST filter by the current tenant. Use the base repository's
  tenant-scoped query helper — never write a raw query that skips it.
  If you write a repository method that does NOT filter by tenant, you
  MUST flag it explicitly and explain why.

- **Repository pattern.** No direct SQLAlchemy session queries from API
  routes or AI tools. All DB access goes through `packages/database/repositories/`.

- **AI tools are thin wrappers.** Files in `app/ai/tools/` call repository
  methods. They contain no business logic of their own beyond input
  validation and formatting the tool result.

- **Audit logging is part of the write path, not bolted on.** Any CUD
  operation that should be audited writes to `audit_log` in the same
  logical operation (not a separate background task, unless the spec
  says otherwise).

- **Errors are typed.** Use the error classes in `packages/shared/errors/`.
  No bare `except Exception` that swallows errors silently.

## Testing expectations

- Every new repository method that should enforce tenant isolation gets
  at least one adversarial test in `tests/adversarial/` that attempts to
  read/write across tenants and asserts it fails.
- Every new API route gets at least one happy-path and one auth-failure
  test.
- Run the relevant test file after implementing — don't just write tests
  and move on without running them.

## Things to NOT build yet (out of scope for V1)

- Lead entity, email/calendar sync, billing/subscriptions
- Multi-agent orchestration, advanced reranking
- Full OpenTelemetry / Grafana / Prometheus server
- MCP server (deferred — see docs/decisions/ for rationale)

If you find yourself about to build any of these, stop and flag it.