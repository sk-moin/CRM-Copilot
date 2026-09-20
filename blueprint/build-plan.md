# Build Plan

List the features that make up your project, high level and in rough build order.
Keep each item to one line; the details come later in `/feature`.

Plain bullets are fine. When both planning docs are ready, run `/overview`.
It adds tracking numbers and checkboxes to your feature list before generating
the project overview.

Run `/feature` to spec the next unchecked item, or `/feature 2` to pick one.
Keep completed items checked and append new features as the project grows.
Do not renumber completed features; their archived specs refer to those IDs.

Scaffolding the app and prototyping its look are pre-build steps, not features.
Start with your first real slice of functionality.

## Your features

### V1

- [x] 000. **DB Foundations** - Tenant → Organization → User schema, Alembic migrations, and the tenant-scoped repository pattern every later spec depends on
- [x] 001. **Auth & RBAC** - JWT access + Redis-backed refresh tokens, role-based access (Owner/Admin/Manager/Member), tenant-aware auth endpoints
- [x] 002. **CRM Core** - Multi-tenant CRUD for Companies, Contacts, Opportunities, Tasks, and Notes
- [x] 003. **Audit & Activity** - Immutable audit log on every CRM mutation plus entity/user/tenant activity feeds — foundation for the Agent, Prompt Management, Guardrails, and Approval Layer specs
- [x] 004. **Streaming Chat** - Persistent conversations, immutable message history, and SSE-streamed LLM responses behind a provider abstraction
- [x] 005. **RAG Foundation (LangChain)** - Document ingestion, chunking, embeddings, and pgvector retrieval wired into chat
- [x] 006. **Retrieval Observability (LangSmith)** - Automatic tracing of retrieval calls — latency, retrieved chunks, failures — with no change to business logic
- [x] 007. **AI Agent Orchestration (LangGraph)** - Deterministic agent graph replacing the direct RAG chain; coordinates retrieval, prompting, generation, and streaming
- [x] 008. **Prompt Management** - Centralized, versioned, tenant-aware prompt store replacing hardcoded prompts across the agent
- [x] 009. **AI Guardrails & Safety (NVIDIA NeMo Guardrails)** - Input/output rails governing the chat and RAG response paths, guarding against jailbreaks, prompt injection, off-topic responses, prompt/secret leakage and unsafe content
- [ ] 010. **AI Actions & Approval Layer** - Lets the agent propose CRM-mutating actions that route through human approval before executing, building on the Spec 003 audit trail
- [ ] 011. **Background Jobs** - Async task queue for long-running work (ingestion, embeddings, eval runs) off the request/response path
- [ ] 012. **Rate Limiting** - Redis-backed per-tenant/per-user request throttling via fastapi-limiter
- [ ] 013. **Observability** - Structured logging, metrics, and tracing across the API and agent layers, beyond the retrieval-only tracing from Spec 006
- [ ] 014. **AI Evaluation Framework** - Automated regression + LLM-as-judge eval suite for agent responses and retrieval quality

### V2

- [ ] 015. **Typed Repositories** - Strongly-typed generics across the `packages/database/repositories` layer
- [ ] 016. **Lead Management** - New Lead entity and pipeline stages, extending CRM Core beyond Companies/Contacts/Opportunities
- [ ] 017. **Email Integration** - Inbound/outbound email sync tied to CRM contacts and conversations
- [ ] 018. **Calendar Integration** - Calendar sync for scheduling meetings and tasks from the CRM and agent
- [ ] 019. **Billing & Quotas** - Subscription billing and per-tenant usage quota enforcement
- [ ] 020. **Feature Flags** - Per-tenant/per-user flagging to roll features out incrementally
- [ ] 021. **Webhooks** - Outbound event delivery for CRM and AI events to external systems
- [ ] 022. **Knowledge Connectors** - Ingestion connectors (e.g. Drive, Notion, Slack) feeding the RAG pipeline beyond manual document upload
- [ ] 023. **AI Copilot Skills** - Reusable, composable agent tools beyond the current tool set
- [ ] 024. **AI Analytics** - Usage and performance analytics over agent conversations and actions
- [ ] 025. **Conversation Replay** - Step-by-step replay of past agent runs for debugging and review
- [ ] 026. **Prompt Versioning** - Diffing, rollback, and A/B rollout on top of the Spec 008 prompt store
- [ ] 027. **Data Retention** - Configurable retention and deletion policies for conversations, documents, and audit data
- [ ] 028. **PII Redaction** - Detect and redact PII in stored conversations, documents, and agent outputs
- [ ] 029. **GraphRAG Knowledge Layer** - Graph-based retrieval (Neo4j) alongside the vector RAG pipeline for multi-hop, relationship-aware queries
- [ ] 030. **Semantic Cache** - Cache semantically-similar LLM/retrieval calls to cut latency and cost
- [ ] 031. **Advanced Reranking** - Cross-encoder/LLM reranking of retrieved chunks before generation
- [ ] 031a. **Groundedness Rail** - Check agent answers against retrieved chunks to catch hallucinated CRM facts; descoped from 009, which shipped without it

### V3

- [ ] 032. **Workflow Automation Engine** - Trigger/condition/action automations across CRM and AI events
- [ ] 033. **Multi-Agent Orchestration** - Multiple specialized LangGraph agents coordinating on a single task
- [ ] 034. **Multi-Model Gateway** - Unified routing and fallback across multiple LLM providers, beyond the single OpenRouter path
- [ ] 035. **MCP Server** - Expose CRM Copilot's tools and data over MCP for external agent clients
- [ ] 036. **Full Observability Stack** - OpenTelemetry + Grafana/Prometheus, superseding the lighter Spec 013 observability
- [ ] 037. **Global Admin Dashboard** - Cross-tenant admin console for platform operators
- [ ] 038. **Long-Term Memory** - Persistent, retrievable agent memory that spans beyond a single conversation
- [ ] 039. **Human-in-the-Loop Analytics** - Metrics on approval-layer decisions and human overrides of agent actions
- [ ] 040. **Enterprise Features** - SSO, advanced RBAC, and other enterprise-tier requirements
- [ ] 041. **Real-Time Voice Agent** - Low-latency voice interface into the agent, extending the Spec 004 streaming/provider abstraction
- [ ] 042. **AI SDR Agent** - Autonomous outbound sales-development agent built on the Actions & Approval layer
