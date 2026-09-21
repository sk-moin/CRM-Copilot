# CRM Copilot - Project Overview

<!-- blueprint:source-hash 207d0e7a7a6d48260acd98dc3f02724f5332f5c9898cbe301194302eae42de28 -->

> A multi-tenant CRM with a guardrailed, RAG-grounded AI agent that answers
> natural-language questions about the org's own records and documents, built to
> run on free-tier infrastructure.

## Problem

Sales and account teams lose time digging through CRM records and related
documents to answer routine questions ("what's the status of the ABC Ltd.
contract", "what's our pipeline this month") and to keep activity logs current.

CRM Copilot pairs a standard multi-tenant CRM with a RAG + tool-calling AI agent
grounded in the org's own data, and — from feature 010 onward — proposes CRM
actions for a human to approve rather than acting unsupervised. The whole stack
targets free tiers (Neon, Upstash, OpenRouter, local embeddings), so the AI layer
doesn't require enterprise infrastructure spend.

## Users

Small-to-mid-size sales/ops teams, each isolated as its own tenant organization.
Access is role-differentiated within a team:

- **Owner** - top of the internal hierarchy
- **Admin** - administrative access within the org
- **Manager** - team-level access
- **Member** - default role

Enterprise features (SSO, advanced RBAC) are explicitly deferred to V3, so V1
targets teams that don't need enterprise procurement, not large enterprises.

## Usage model

| Constraint | Established position |
|---|---|
| Tenancy | Multi-tenant, non-negotiable. Every tenant-owned table carries `tenant_id`, every repository query filters by it, and tenant isolation gets adversarial tests. |
| Operation | Internet-facing SaaS, not an internal tool. |
| Trust model | Users within a tenant are trusted collaborators under an internal role hierarchy. The adversarial threat model is cross-tenant boundary violations, not individual end users. |
| Audit | Every CRM mutation writes an immutable `audit_log` entry in the same operation, for compliance and auditability. No specific certification (SOC 2, GDPR, etc.) is named. |
| Scale | Not established. |

Explicit non-requirements for now: Lead entity, email/calendar sync,
billing/subscriptions, multi-agent orchestration, advanced reranking, a full
OpenTelemetry/Grafana/Prometheus stack, and an MCP server — all deferred to
V2/V3.

## Features

Build-plan order. V1 items 000-010 are shipped; 011 is the current edge.

**V1**

1. **000. DB Foundations** - Tenant -> Organization -> User schema, Alembic migrations, and the tenant-scoped repository pattern every later feature depends on.
2. **001. Auth & RBAC** - JWT access tokens plus Redis-backed rotating refresh tokens, with Owner/Admin/Manager/Member role checks on tenant-aware auth endpoints.
3. **002. CRM Core** - Multi-tenant CRUD for Companies, Contacts, Opportunities, Tasks, and Notes.
4. **003. Audit & Activity** - Immutable audit log on every CRM mutation plus entity/user/tenant activity feeds; the foundation the Agent, Prompt Management, Guardrails, and Approval Layer all build on.
5. **004. Streaming Chat** - Persistent conversations, immutable message history, and SSE-streamed LLM responses behind a provider abstraction.
6. **005. RAG Foundation (LangChain)** - Document ingestion, chunking, embeddings, and pgvector retrieval wired into chat. **Headline capability.**
7. **006. Retrieval Observability (LangSmith)** - Automatic tracing of retrieval latency, retrieved chunks, and failures with no change to business logic.
8. **007. AI Agent Orchestration (LangGraph)** - Deterministic agent graph replacing the direct RAG chain; coordinates retrieval, prompting, generation, and streaming.
9. **008. Prompt Management** - Centralized, versioned, tenant-aware prompt store replacing hardcoded prompts across the agent.
10. **009. AI Guardrails & Safety (NeMo Guardrails)** - Input and output rails governing the chat and RAG response paths against jailbreaks, prompt injection, off-topic responses, prompt and secret leakage, and unsafe content. PII redaction and groundedness were descoped to 028 and 031a.
11. **010. AI Actions & Approval Layer** - The agent proposes CRM mutations as durable `AgentAction` records; a person approves, and only then does the mutation execute, exactly once. Every transition is audited. Proposals are parsed from a structured block in the model's answer; native tool calling is deferred to 023.
12. **011. Background Jobs** - Async task queue for ingestion, embeddings, and eval runs off the request/response path.
13. **012. Rate Limiting** - Redis-backed per-tenant/per-user throttling via `fastapi-limiter`.
14. **013. Observability** - Structured logging, metrics, and tracing across API and agent layers, beyond 006's retrieval-only tracing.
15. **014. AI Evaluation Framework** - Automated regression and LLM-as-judge eval suite for agent responses and retrieval quality.

**V2** - 015 Typed Repositories, 016 Lead Management, 017 Email Integration,
018 Calendar Integration, 019 Billing & Quotas, 020 Feature Flags, 021 Webhooks,
022 Knowledge Connectors, 023 AI Copilot Skills, 024 AI Analytics,
025 Conversation Replay, 026 Prompt Versioning, 027 Data Retention,
028 PII Redaction, 029 GraphRAG Knowledge Layer, 030 Semantic Cache,
031 Advanced Reranking.

**V3** - 032 Workflow Automation Engine, 033 Multi-Agent Orchestration,
034 Multi-Model Gateway, 035 MCP Server, 036 Full Observability Stack,
037 Global Admin Dashboard, 038 Long-Term Memory,
039 Human-in-the-Loop Analytics, 040 Enterprise Features,
041 Real-Time Voice Agent, 042 AI SDR Agent.

See `blueprint/build-plan.md` for the tracked checklist and the one-line
description of each V2/V3 item.

## Data model

All IDs are `UUID` (PostgreSQL `gen_random_uuid()`). Every tenant-owned table
carries `tenant_id` and every repository query filters by it. This is the locked
isolation contract, not a convention.

### Tenancy

**Tenant** - `name`, `subdomain` (unique), `created_at`.

**Organization** - `tenant_id` -> Tenant (cascade), `name`, `subdomain`
(unique), `domain` (nullable), `created_at`.

**User** - `tenant_id` -> Tenant, `org_id` -> Organization, `email` (unique),
`password_hash`, `role` (enum `OWNER|ADMIN|MANAGER|MEMBER`, default `MEMBER`),
`created_at`.

> Locked. Every later model hangs off `tenant_id` / `org_id`.

### CRM core

**Company** - `tenant_id`, `org_id`, `name`, `industry?`, `website?`, `phone?`,
`email?`, `address?`, timestamps.

**Contact** - `tenant_id`, `org_id`, `company_id` -> Company, `first_name`,
`last_name`, `email?`, `phone?`, `job_title?`, timestamps.

**Opportunity** - `tenant_id`, `org_id`, `company_id` -> Company,
`owner_user_id` -> User, `title`, `stage`, `probability?` (int), `value?`
(decimal), `expected_close_date?`, timestamps.

**Task** - `tenant_id`, `org_id`, `assigned_to_user_id` -> User, polymorphic
`entity_type?` / `entity_id?`, `title`, `description?`, `status`, `priority`,
`due_date?`, timestamps.

**Note** - `org_id`, polymorphic `entity_type` / `entity_id`, `content`,
timestamps.

> Task and Note attach to any CRM entity through the `entity_type` /
> `entity_id` pair rather than per-entity foreign keys.

### Conversations

**Conversation** - `tenant_id`, `org_id`, `user_id` -> User, `title`, `status`,
`created_at`, `updated_at`, `deleted_at?` (soft delete).

**Message** - `conversation_id` -> Conversation, `tenant_id`, `role`, `content`,
`model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `latency_ms`,
`finish_reason`, `message_metadata` (JSON), `created_at`.

> Messages are immutable. Message-level feedback rides in `message_metadata`.

### Knowledge / RAG

**KnowledgeDocument** - `tenant_id`, `org_id`, `owner_id` -> User, `title`,
`filename`, `storage_path`, `document_type`, `source_type`, `mime_type`,
`file_size`, `processing_status` (enum
`UPLOADED|PARSING|CHUNKING|EMBEDDING|READY|FAILED|COMPLETED`),
`processing_started_at?`, `processed_at?`, `error_message?`, `chunk_count`,
timestamps.

**DocumentChunk** - `tenant_id`, `document_id` -> KnowledgeDocument,
`chunk_index`, `content`, `token_count`, `embedding` (pgvector),
`chunk_metadata` (JSON), `start_char`, `end_char`, `created_at`.

> `embedding` dimensionality is fixed by `BAAI/bge-base-en-v1.5`. Changing the
> embedding model requires a migration and a full re-embed.

### Prompts

**Prompt** - `tenant_id`, `org_id` -> Organization, `name`, `category`
(`PromptCategory`), `description?`, `active_version_id` -> PromptVersion,
timestamps.

**PromptVersion** - `prompt_id` -> Prompt, `version` (int), `description?`,
`template`, `variables` (JSON), `llm_model?`, `temperature`, `top_p`,
`max_tokens?`, `response_format`, `config` (JSON), `created_by` -> User,
`created_at`.

> Versions are append-only; a Prompt points at exactly one active version.

### Retrieval observability

**RetrievalTrace** - `tenant_id`, `conversation_id` -> Conversation, `query`,
`embedding_model`, `vector_store`, `embedding_latency_ms`,
`retrieval_latency_ms`, `total_latency_ms`, `retrieved_chunks` (count),
`status`, `error_message?`, `retrieval_metadata` (JSON), timestamps.

**RetrievedChunk** - `tenant_id`, `trace_id` -> RetrievalTrace, `document_id`,
`chunk_id`, `rank`, `similarity_score`, `chunk_preview`, `retrieval_metadata`
(JSON), timestamps.

### Agent actions

**AgentAction** - `tenant_id`, `org_id`, `conversation_id?` -> Conversation,
`proposed_by_user_id` -> User, `action_type` (enum, five allowed CRM
mutations), `payload` (JSONB, validated against a strict per-type schema),
`reason?`, `status` (enum `PENDING|APPROVED|REJECTED|EXECUTED|FAILED`),
`decided_by_user_id?` -> User, `decided_at?`, `decision_reason?`,
`executed_at?`, `result_entity_type?`, `result_entity_id?`, `error_message?`,
`correlation_id`, timestamps. Indexed on `(tenant_id, status)`.

> Executes at most once: the PENDING check and the status write share a row
> lock. Scoped by org as well as tenant, because the executor stamps the CRM
> row with the approver's org.

### Compliance

**AuditLog** - `tenant_id`, `org_id`, `user_id`, `entity_type`, `entity_id`,
`action`, `before_values` (JSON), `after_values` (JSON), `ip_address`,
`user_agent`, `actor_type`, `correlation_id`, `event_metadata` (JSON),
`created_at`.

> One immutable row per CRM mutation, written in the same operation as the
> mutation. Never updated or deleted. `actor_type` distinguishes human from
> agent actions, which feature 010's approval layer depends on.

## Tech stack

| Layer | Choice | Role |
|---|---|---|
| Backend | FastAPI (Python 3.12) | REST API under `/api/v1`, health check at `/health` |
| ORM / migrations | SQLAlchemy 2.x (async), Alembic | Data access and schema evolution |
| Database | PostgreSQL + pgvector | Neon free tier in production; local via `docker-compose` (`pgvector/pgvector:pg16`) |
| Cache | Redis (Upstash / Redis Cloud free tier) | Refresh tokens, rate-limit counters, short-term memory only, never durable storage |
| RAG | LangChain | Ingestion, chunking, retrieval chain |
| Agent | LangGraph | Deterministic agent graph |
| Tracing | LangSmith | Retrieval tracing (feature 006) |
| Guardrails | NVIDIA NeMo Guardrails | Input/output rails (feature 009, in progress) |
| LLM access | Groq (OpenAI-compatible), default `openai/gpt-oss-20b` | OpenRouter and a deterministic mock swappable behind one provider interface |
| Embeddings | local `BAAI/bge-base-en-v1.5` via sentence-transformers | No embedding API cost |
| Auth | PyJWT (15-min access) + rotating refresh tokens in Redis, bcrypt passwords | RBAC via role claim |
| Rate limiting | `fastapi-limiter` (Redis-backed) | Feature 012 |
| Frontend | Next.js 15 (App Router), TypeScript, TanStack Query | Not present in this repo — see Open questions |
| Testing | pytest (backend), vitest (frontend) | Backend gate only until the frontend exists |

## Monetization

Not decided. No billing code exists beyond the **019 Billing & Quotas** roadmap
item. Two models fit this product shape without much rework:

- Per-seat subscription, priced off the Owner/Admin/Manager/Member roles already
  modeled.
- Seat price plus usage-based AI credits, once quotas exist.

Worth deciding before 019 is spec'd, since the answer determines what Quotas has
to enforce.

## UI/UX

A standard SaaS dashboard shell, already established in `Demo-UI-Dashboard.png`:

- **App shell** - fixed dark sidebar (logo, primary nav, org switcher, user
  footer) beside a light content area.
- **Dashboard** - KPI cards, a pipeline funnel chart, an activity feed, and data
  tables with stage pills.
- **AI Copilot** - a persistent right-hand panel, not a popup. Mixes
  plain-language answers with structured result cards (for example a contract
  card with its source and a "View Document" link), offers clickable
  suggested-prompt chips, and carries a standing "Responses may not be 100%
  accurate" disclaimer under the composer.

> That disclaimer is already doing informal guardrail messaging. Feature 009's
> NeMo rails should sharpen it, not duplicate it.

> TODO: named routes and screens are not established, because the Next.js
> frontend is not in this repo.

## Deployment

| Item | Value |
|---|---|
| Target host | Not decided. No `Procfile` / `render.yaml` / `fly.toml` / `vercel.json` in the repo. Render, Railway, or Fly.io all pair naturally with Neon + Upstash for the backend; Vercel fits the Next.js frontend once it exists. |
| App entrypoint | `app.main:app` — a stock `uvicorn app.main:app` start command should work as-is |
| Build command | None beyond installing dependencies |
| Health check | `GET /health` (implemented) |
| Database | PostgreSQL + pgvector, Neon free tier (the docker-compose Postgres container is dev-only) |
| Cache | Redis, Upstash / Redis Cloud free tier |
| Workers / cron | None yet — feature 011 (Background Jobs) is unbuilt |
| Domain | Not set |

**Env vars** (names from `.env.example`): `APP_NAME`, `APP_ENV`, `DEBUG`,
`DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_AUDIENCE`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_TTL_SECONDS`, and one of
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`.

> TODO: a Redis connection variable is required by `app/core/redis_client.py`
> but is missing from `.env.example`.

> TODO: no `requirements.txt` or `pyproject.toml` is checked in. Pin
> dependencies before deploying.

## Open questions

> **Frontend state is unconfirmed.** The plan names Next.js 15 + TypeScript +
> TanStack Query and describes an established dashboard UI, but no frontend code
> is in this repo. Either it lives elsewhere or it is not built yet. This also
> makes the `vitest` frontend test gate unverifiable here.

> **Dependencies are not pinned.** No `requirements.txt` or `pyproject.toml` is
> checked in, despite a large dependency surface (FastAPI, SQLAlchemy,
> LangChain, LangGraph, NeMo Guardrails, sentence-transformers).

> **The Redis env var is undocumented.** `app/core/redis_client.py` needs a
> connection string that `.env.example` does not list.

> **Monetization is undecided.** Resolve before feature 019 is spec'd.

> **Expected scale is unestablished.** Left unanswered deliberately; do not
> infer enterprise scale from the multi-tenant design.

> **Two features overlap by design.** Feature 013 (Observability) is superseded
> by feature 036 (Full Observability Stack), and feature 026 (Prompt
> Versioning) extends feature 008. Both are intentional per the plan, but 013's
> V1 scope should be bounded when it is spec'd so it is not rebuilt at 036.
