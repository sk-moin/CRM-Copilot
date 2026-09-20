# Project Plan

> One of the two planning docs you provide. Use as much detail as the project
> needs, including rationale, constraints, examples, edge cases, and explicit
> exclusions that should guide later feature work. Draft it directly, develop it
> through any AI conversation, or optionally run `/discovery` for a guided deep
> planning session. The content is always yours to direct. When it is filled in,
> run `/overview` to generate the project overview from this plus `build-plan.md`.

## 1. Problem - What problem are we solving?

Sales and account teams lose time digging through CRM records and related
documents to answer routine questions ("what's the status of the ABC Ltd.
contract", "what's our pipeline this month") and to keep activity logs current.

CRM Copilot pairs a standard multi-tenant CRM (companies, contacts,
opportunities, tasks, notes) with a RAG + tool-calling AI agent that answers
natural-language questions grounded in the org's own CRM data and uploaded
documents, and — from spec 010 onward — proposes CRM actions for a human to
approve rather than acting unsupervised. The whole stack is built to run on
free tiers (Neon, Upstash, OpenRouter, local embeddings), so the AI layer
doesn't require enterprise infrastructure spend to stand up.

## 2. Users - Who is this for?

Small-to-mid-size sales/ops teams, each isolated as its own tenant
organization. RBAC models an internal hierarchy — Owner, Admin, Manager,
Member — so access within a team is already role-differentiated. Enterprise
features (SSO, advanced RBAC) are explicitly deferred to V3, so V1's target
is teams that don't need enterprise procurement, not large enterprises.

## 3. Features - What does the MVP need?

- Multi-tenant workspaces with role-based access (Owner/Admin/Manager/Member)
- Core CRM records — Companies, Contacts, Opportunities, Tasks, Notes — with full CRUD
- Immutable audit trail and activity timeline on every CRM mutation
- Streaming AI chat grounded in CRM + uploaded knowledge docs via RAG (pgvector)
- Guardrailed agent (NeMo Guardrails) that can propose CRM actions, gated behind human approval
- Tenant-aware, versioned prompt management so agent behavior tunes without a redeploy

## 4. Data - What are we storing?

- **Tenancy**: Tenant, Organization, User (role claim)
- **CRM core**: Company, Contact, Opportunity, Task, Note
- **Conversations**: Conversation, Message (with message-level feedback)
- **Knowledge/RAG**: KnowledgeDocument, DocumentChunk (+ pgvector embeddings)
- **Prompts**: Prompt, PromptVersion
- **Retrieval observability**: RetrievalTrace, RetrievedChunk
- **Compliance**: AuditLog — one immutable row per CRM mutation

## 5. Tech - What stack are we using?

- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.x (async), Alembic — REST API under `/api/v1`, health check at `/health`
- **Database**: PostgreSQL + pgvector — Neon free tier in production, local via `docker-compose` (`pgvector/pgvector:pg16`)
- **Cache**: Redis (Upstash/Redis Cloud free tier) — refresh tokens, rate-limit counters, short-term memory only, never durable storage
- **AI orchestration**: LangChain (RAG), LangGraph (agent graph), LangSmith (retrieval tracing), and NVIDIA NeMo Guardrails going in now (spec 009)
- **LLM access**: OpenRouter (OpenAI-compatible), with OpenAI/Anthropic swappable behind the same provider interface
- **Embeddings**: local `BAAI/bge-base-en-v1.5` via sentence-transformers — no embedding API cost
- **Auth**: JWT (15-min access tokens) + rotating refresh tokens (30-day TTL) in Redis, RBAC via role claim
- **Rate limiting**: `fastapi-limiter` (Redis-backed)
- **Frontend**: Next.js 15 (App Router), TypeScript, TanStack Query per `CLAUDE.md` — not included in this upload, so current build state there is unconfirmed
- **Testing**: pytest (backend), vitest (frontend)

## 6. Monetize - How will this make money?

Not yet decided in the repo — no billing code exists beyond the placeholder
**019 Billing & Quotas** roadmap item. Two models fit this shape of product
without much rework: per-seat subscription (pricing off the
Owner/Admin/Manager/Member roles already modeled), or a seat price plus
usage-based AI credits once quotas exist. Worth deciding before 019 is
spec'd, since the answer determines what Quotas actually needs to enforce.

## 7. UI/UX - How should this look and feel?

Already established (see `Demo-UI-Dashboard.png`): a standard SaaS dashboard
shell — fixed dark sidebar (logo, primary nav, org switcher, user footer),
light content area with KPI cards, a pipeline funnel chart, an activity feed,
and data tables with stage pills.

The AI Copilot is a persistent right-hand panel, not a popup. It mixes
plain-language answers with structured result cards (e.g. a contract card
with source + "View Document" link), offers clickable suggested-prompt
chips, and carries a standing "Responses may not be 100% accurate"
disclaimer under the composer. That disclaimer is worth keeping in mind for
spec 009 — it's already doing informal guardrail messaging that NeMo's rails
should sharpen, not duplicate.

## 8. Deployment - Where and how will this ship?

- **Health check**: `GET /health` (already implemented)
- **App entrypoint**: `app.main:app` — a stock `uvicorn app.main:app` start command should work as-is
- **Build command**: none beyond installing dependencies — flagging that no `requirements.txt`/`pyproject.toml` is checked into this upload, so pin one before deploying
- **Database**: PostgreSQL + pgvector, Neon free tier per `CLAUDE.md` (the docker-compose Postgres container is dev-only)
- **Cache**: Redis, Upstash/Redis Cloud free tier
- **Env vars** (names from `.env.example`): `APP_NAME`, `APP_ENV`, `DEBUG`, `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_AUDIENCE`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_TTL_SECONDS`, one of `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/`OPENROUTER_API_KEY` — plus a Redis connection var, which isn't in `.env.example` yet despite `app/core/redis_client.py` needing one
- **Workers/cron**: none yet — spec 011 (Background Jobs) is still unbuilt
- **Target host**: not decided — no `Procfile`/`render.yaml`/`fly.toml`/`vercel.json` in the repo. Render, Railway, or Fly.io would all pair naturally with the Neon + Upstash free-tier setup for the backend; Vercel is the natural fit for the Next.js 15 frontend once it exists
- **Domain**: not yet set

## 9. Usage model and constraints (optional)

- **Tenancy**: multi-tenant, confirmed and non-negotiable per `CLAUDE.md` — every tenant-owned table carries `tenant_id`, every repository query must filter by it, and tenant isolation gets adversarial tests
- **Operation**: internet-facing SaaS, not an internal tool
- **Trust model**: users within a tenant are trusted collaborators under an internal role hierarchy; the adversarial threat model is specifically cross-tenant boundary violations, not individual end users
- **Audit/compliance**: every CRM mutation writes an immutable `audit_log` entry in the same operation, built explicitly for "compliance and auditability requirements" per spec 003 — though no specific certification (SOC 2, GDPR, etc.) is named anywhere in the repo
- **Explicit non-requirements for now** (per `CLAUDE.md`): Lead entity, email/calendar sync, billing/subscriptions, multi-agent orchestration, advanced reranking, a full OpenTelemetry/Grafana/Prometheus stack, and an MCP server — all deliberately deferred to V2/V3
- **Expected scale**: not established anywhere in the repo — left unanswered rather than guessed, per the note above
