# Session 008 – Prompt Management

**Status:** ✅ Completed
**Date:** 2026-07-19 – 2026-07-26

---

# Overview

This session completed the Prompt Management system for CRM Copilot.

The objective of this specification was to provide a production-ready prompt management layer that allows prompts to be versioned, managed through the API, rendered dynamically, cached, and consumed by the AI agent without hardcoding prompt templates into the application.

The implementation introduces database-backed prompt templates, prompt versioning, rendering using Jinja2, tenant isolation, caching, and integration into the LangGraph-based AI workflow.

---

# Objectives

Completed objectives:

- Database-backed prompt management
- Prompt versioning
- Active version selection
- Prompt rendering using Jinja2
- Prompt caching
- Prompt loading abstraction
- Prompt manager abstraction
- CRUD Prompt API
- CRUD Prompt Version API
- Activate Prompt Version API
- Prompt rendering endpoint
- Tenant isolation
- Repository layer
- Unit tests
- Repository tests
- API tests
- Agent integration

---

# Architecture

The implementation separates responsibilities into dedicated layers.

## Database

- Prompt
- PromptVersion

Each prompt can have multiple versions.

Only one version may be active at any time.

---

## Repository Layer

Implemented repositories:

- PromptRepository
- PromptVersionRepository

Responsibilities:

- CRUD operations
- Tenant scoping
- Active version retrieval
- Version activation
- Organization filtering

---

## Service Layer

### PromptLoader

Responsibilities

- Load active prompt
- Cache prompt versions
- Retrieve active template
- Cache invalidation

---

### PromptRenderer

Responsibilities

- Render Jinja2 templates
- Variable substitution
- Safe rendering
- Template compilation

---

### PromptCache

Responsibilities

- In-memory prompt cache
- Cache lookup
- Cache invalidation
- Cache clearing

---

### PromptManager

High-level API combining:

- PromptLoader
- PromptRenderer

Responsibilities

- Get prompt
- Render prompt
- Check prompt existence
- Invalidate cache
- Clear cache

---

# API

Implemented endpoints

## Prompt

```
POST   /api/v1/prompts
GET    /api/v1/prompts
GET    /api/v1/prompts/{id}
PUT    /api/v1/prompts/{id}
DELETE /api/v1/prompts/{id}
```

---

## Prompt Versions

```
POST /api/v1/prompts/{id}/versions
GET  /api/v1/prompts/{id}/versions
```

---

## Activation

```
POST /api/v1/prompts/{id}/activate/{version_id}
```

---

## Rendering

```
POST /api/v1/prompts/{id}/render
```

Allows rendering a prompt with supplied variables before deployment.

---

# Agent Integration

Prompt management is integrated into the AI workflow.

Instead of hardcoded prompts:

```
Prompt
      ↓
PromptLoader
      ↓
PromptManager
      ↓
PromptRenderer
      ↓
Agent
```

The AI agent now retrieves the currently active prompt version dynamically.

---

# Features

## Prompt Versioning

Each prompt supports unlimited versions.

Example

Version 1

```
You are a CRM assistant.
```

Version 2

```
You are an expert CRM sales assistant.
```

Only one version is active.

---

## Active Version Switching

Versions can be activated without restarting the application.

No code deployment is required.

---

## Jinja2 Rendering

Templates support variables.

Example

```
Hello {{ customer_name }}

Today's opportunity value is {{ amount }}.
```

---

## Prompt Caching

Frequently used prompts are cached.

Benefits

- fewer database queries
- faster prompt retrieval
- lower latency

---

## Tenant Isolation

All repositories remain tenant scoped.

Prompts belonging to another tenant cannot be accessed.

---

# Testing

Completed test suites

## Repository Tests

- PromptRepository
- PromptVersionRepository

Validated

- CRUD
- version activation
- tenant isolation
- filtering
- active version retrieval

---

## Service Tests

PromptLoader

PromptRenderer

PromptManager

Validated

- rendering
- cache usage
- prompt retrieval
- variable substitution
- missing prompts
- latest active version
- cache invalidation

---

## API Tests

Validated

- CRUD endpoints
- version endpoints
- activation endpoint
- rendering endpoint

---

# Refactoring Performed

During implementation the prompt system evolved beyond the original specification.

Major improvements include:

- PromptLoader abstraction
- PromptRenderer abstraction
- PromptManager orchestration layer
- Dedicated PromptCache
- Cleaner separation of concerns
- Better dependency injection
- Improved testability

---

# Issues Encountered

Several breaking changes occurred during development.

## PromptManager constructor

Originally accepted repositories directly.

Refactored to accept:

- PromptLoader
- PromptRenderer

All tests were updated accordingly.

---

## AgentService

Added

```
org_id
```

to support organization-scoped prompt loading.

This required updates to

- AgentService tests
- ChatService tests
- fake services

---

## PromptRenderer

Rendering behavior was updated so missing variables no longer raise exceptions, matching the desired Jinja2 behavior used throughout the application.

---

## Tenant Isolation

A repository issue allowed PromptVersion retrieval across tenants.

The repository query was updated to join Prompt and enforce tenant filtering.

---

# Test Results

Final project status

```
356 tests passed
0 failures
```

All Prompt Management components are fully covered by automated tests.

---

# Specification Status

| Component | Status |
|----------|--------|
| Prompt Model | ✅ |
| PromptVersion Model | ✅ |
| Repositories | ✅ |
| CRUD API | ✅ |
| Version API | ✅ |
| Activation API | ✅ |
| Rendering API | ✅ |
| PromptLoader | ✅ |
| PromptRenderer | ✅ |
| PromptCache | ✅ |
| PromptManager | ✅ |
| Agent Integration | ✅ |
| Tenant Isolation | ✅ |
| Tests | ✅ |

---

# Notes

The implemented architecture intentionally differs slightly from the original specification.

Instead of a monolithic PromptManager accessing repositories directly, responsibilities are separated into dedicated components:

- PromptLoader
- PromptRenderer
- PromptCache
- PromptManager

This provides better maintainability, testability, and extensibility while preserving all functional requirements of the Prompt Management specification.

Prompt templates are database-backed, versioned, tenant-aware, cacheable, dynamically rendered, and integrated into the AI agent pipeline.

---

# Result

✅ Spec 008 – Prompt Management completed successfully.

The CRM Copilot now supports production-ready prompt management with versioning, caching, rendering, tenant isolation, API management, and seamless integration into the LangGraph-based AI workflow.