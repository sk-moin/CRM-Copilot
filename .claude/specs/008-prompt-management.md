# Spec 008 – Prompt Management


**Dependencies**
- ✅ Spec 000 – Database Foundations
- ✅ Spec 001 – Authentication & RBAC
- ✅ Spec 002 – CRM Core
- ✅ Spec 003 – Audit & Activity
- ✅ Spec 004 – Streaming Chat
- ✅ Spec 005 – RAG Pipeline
- ✅ Spec 006 – Retrieval Observability
- ✅ Spec 007 – AI Agent

---

# Overview

As AI capabilities grow, prompt engineering becomes application logic. Hardcoded prompts quickly become difficult to maintain, impossible to version, and risky to modify. Prompt Management introduces a centralized, version-controlled, tenant-aware system for managing all prompts used by the CRM Copilot platform.

Instead of embedding prompt strings inside LangGraph nodes, services, or repositories, every AI interaction will retrieve prompts through a dedicated Prompt Management layer. This enables prompt versioning, tenant customization, runtime updates, reproducibility, and future evaluation workflows.

Prompt Management becomes the single source of truth for every system prompt, tool prompt, agent prompt, summarization prompt, and retrieval prompt used throughout the platform.

---

# Goals

- Centralize all prompts
- Eliminate hardcoded prompt strings
- Support immutable prompt versioning
- Support tenant-specific overrides
- Validate prompt variables before rendering
- Support reusable prompt templates
- Enable runtime prompt updates
- Cache frequently used prompts
- Record prompt versions used for AI requests
- Prepare foundation for Guardrails and Evaluation Framework

---

# Non-Goals

This specification does **not** include:

- AI Safety Rules (Spec 009)
- Prompt Evaluation (Spec 014)
- Prompt Experiments / A/B Testing
- Human Approval Workflows
- Dynamic Prompt Optimization

---

# Architecture

```
                 LangGraph Nodes
                        │
                        ▼
               PromptBuilder
                        │
                        ▼
               PromptManager
                /        |        \
               /         |         \
              ▼          ▼          ▼
      Prompt Cache   Prompt Renderer   Prompt Repository
                               │
                               ▼
                       Prompt Versions
                               │
                               ▼
                          PostgreSQL
```

---

# Directory Structure

```
app/
    services/
        llm/
            prompt_builder.py        (existing)
            prompt_manager.py
            prompt_renderer.py
            prompt_cache.py
            prompt_registry.py
            prompt_loader.py
            exceptions.py

            templates/
                system/
                agent/
                rag/
                tools/

packages/
    database/
        models/
            prompt.py
            prompt_version.py

        repositories/
            prompt_repository.py
            prompt_version_repository.py

app/
    api/
        routers/
            prompts.py

        schemas/
            prompt.py
```

---

# Database Design

## Prompt

Represents the logical prompt.

Examples:

- crm_chat
- retrieval_context
- summarize_conversation
- classify_intent
- task_generator

### Fields

| Field | Type |
|--------|------|
| id | UUID |
| organization_id | UUID (nullable) |
| name | String |
| category | Enum |
| description | Text |
| active_version_id | UUID |
| created_at | Timestamp |
| updated_at | Timestamp |

---

## PromptVersion

Each prompt may have many immutable versions.

### Fields

| Field | Type |
|--------|------|
| id | UUID |
| prompt_id | UUID |
| version | Integer |
| template | Text |
| variables | JSON |
| model_name | String |
| temperature | Float |
| top_p | Float |
| max_tokens | Integer |
| response_format | JSON |
| metadata | JSON |
| created_by | UUID |
| created_at | Timestamp |

Prompt versions are immutable.

Updating a prompt always creates a new PromptVersion.

---

# Prompt Categories

```
SYSTEM
AGENT
RAG
TOOL
SUMMARIZATION
CLASSIFICATION
ACTION
CUSTOM
```

---

# Prompt Templates

Templates use Jinja2 syntax.

Example:

```jinja
You are an AI CRM assistant.

Organization:
{{ organization }}

Conversation History:
{{ history }}

Retrieved Context:
{{ context }}

Current User Message:
{{ message }}

Answer professionally using only available information.
```

---

# Prompt Variables

Every PromptVersion declares the variables it requires.

Example:

```json
[
    "organization",
    "history",
    "context",
    "message"
]
```

During rendering the Prompt Renderer validates:

- missing variables
- unknown variables
- invalid values

before rendering.

---

# Prompt Renderer

Responsibilities:

- Render Jinja templates
- Validate required variables
- Escape invalid values where necessary
- Raise descriptive exceptions
- Return final rendered prompt

Example:

```python
rendered = renderer.render(
    template=template,
    variables={
        "history": "...",
        "context": "...",
        "message": "...",
    }
)
```

---

# Prompt Manager

The PromptManager becomes the public interface used by the application.

Responsibilities:

- Load prompts
- Resolve tenant overrides
- Retrieve active version
- Use cache
- Validate variables
- Render templates
- Return rendered prompt

Example:

```python
prompt = await prompt_manager.render(
    name="crm_chat",
    organization_id=org_id,
    variables={
        ...
    }
)
```

---

# Prompt Resolution Order

When requesting a prompt:

```
Organization Prompt
        │
        ▼
Global Prompt
        │
        ▼
Built-in Default
```

This allows organizations to customize prompts without affecting others.

---

# Prompt Cache

Frequently used prompts should not hit the database every request.

Cache Key

```
organization_id
prompt_name
version
```

Cache invalidation occurs whenever:

- prompt updated
- new version activated
- prompt deleted

---

# Built-in Prompt Loader

The project ships with default prompts inside:

```
templates/
```

On application startup:

- check database
- if prompt missing
- insert default version

This guarantees required prompts always exist.

---

# Prompt Builder Integration

Current prompt construction logic inside:

```
prompt_builder.py
```

should delegate to PromptManager.

Instead of:

```python
SYSTEM_PROMPT = """
...
"""
```

it becomes:

```python
await prompt_manager.render(...)
```

PromptBuilder remains responsible for assembling messages.

PromptManager becomes responsible for generating prompt text.

---

# LangGraph Integration

Every LangGraph node should obtain prompts through PromptManager.

Example:

```
Agent Node

↓

PromptManager

↓

Rendered Prompt

↓

LLM
```

No node should contain embedded prompt text.

---

# API Endpoints

## List Prompts

```
GET /api/prompts
```

---

## Get Prompt

```
GET /api/prompts/{id}
```

---

## Create Prompt

```
POST /api/prompts
```

---

## Update Prompt

Creates a new PromptVersion.

```
PUT /api/prompts/{id}
```

---

## Activate Version

```
POST /api/prompts/{id}/versions/{version}/activate
```

---

## List Versions

```
GET /api/prompts/{id}/versions
```

---

## Render Prompt

Debug endpoint.

```
POST /api/prompts/render
```

Returns rendered prompt without invoking an LLM.

---

# Security

Only administrators may:

- Create prompts
- Update prompts
- Activate versions
- Delete prompts

Regular users may never modify prompts.

All prompt changes generate Audit Logs.

---

# Repository Layer

PromptRepository

Responsibilities:

- CRUD
- Active version lookup
- Tenant lookup
- Prompt search

PromptVersionRepository

Responsibilities:

- Create version
- List versions
- Retrieve version
- Activate version

---

# Exceptions

```
PromptNotFoundError

PromptVersionNotFoundError

PromptValidationError

PromptRenderError

MissingPromptVariableError

DuplicatePromptError
```

---

# Audit Logging

Every prompt modification generates an Audit Event.

Examples:

```
PROMPT_CREATED

PROMPT_UPDATED

PROMPT_VERSION_CREATED

PROMPT_VERSION_ACTIVATED

PROMPT_DELETED
```

---

# Observability

Future AI request logs should include:

```
Prompt Name

Prompt Version

Model

Temperature

Max Tokens

Organization
```

This enables reproducibility.

---

# Testing

## Unit Tests

Prompt Renderer

- render template
- missing variable
- extra variable
- invalid syntax

Prompt Manager

- cache hit
- cache miss
- tenant override
- fallback

Repositories

- CRUD
- active version
- version activation

---

## Integration Tests

API

- create prompt
- update prompt
- activate version
- render endpoint

Authorization

- admin allowed
- user forbidden

Database

- prompt version creation
- tenant override
- active version lookup

---

# Acceptance Criteria

- No hardcoded prompts remain inside LangGraph nodes.
- PromptManager is the single interface for prompt retrieval.
- Prompt templates support Jinja rendering.
- Prompt versions are immutable.
- Active versions are configurable.
- Tenant-specific overrides are supported.
- Prompt rendering validates required variables.
- Frequently used prompts are cached.
- Prompt CRUD API is implemented.
- Prompt changes are audited.
- Prompt metadata is available for future evaluation and observability.
- Existing AI functionality continues working without behavioral regressions.

---

# Future Enhancements (Out of Scope)

These are intentionally deferred to later specifications:

- Prompt A/B testing
- Prompt scoring
- Prompt evaluation pipelines
- Automatic prompt optimization
- Multi-model prompt variants
- Prompt performance analytics
- Prompt rollback recommendations
- Semantic prompt search
- Prompt import/export
- Visual prompt editor
- LLM-generated prompt suggestions

These capabilities will naturally build upon the Prompt Management infrastructure introduced in Spec 008.