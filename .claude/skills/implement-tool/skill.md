---
name: implement-tool
description: Implement a reusable AI Tool for the CRM Copilot LangGraph agent. Tools encapsulate a single capability (database access, CRM actions, external APIs, or utility functions) and can be invoked by agent nodes or future function-calling models.
---

# Implement AI Tool

## Goal

Implement a production-ready AI Tool following the CRM Copilot architecture.

A Tool represents one reusable capability that can be called by AI agents, LangGraph nodes, or future function-calling LLMs.

Each tool should perform exactly one action and expose a clean asynchronous interface.

---

# Responsibilities

This skill is responsible for:

- Creating AI tools
- Encapsulating one capability
- Calling services
- Returning structured results
- Input validation
- Error handling

This skill is NOT responsible for:

- HTTP endpoints
- Repository implementation
- Prompt building
- LangGraph orchestration
- Conversation management

---

# Project Structure

Tools are located in

```
app/agent/tools/
```

Examples

```
search_contacts.py
search_companies.py
search_tasks.py
create_task.py
update_opportunity.py
knowledge_search.py
```

---

# Single Responsibility

Each tool performs exactly one task.

Good examples

```
Search Companies

Search Contacts

Create Task

Update Opportunity

Search Knowledge Base
```

Bad example

```
Search contacts

↓

Create task

↓

Send email

↓

Generate response
```

Never combine multiple business workflows into one tool.

---

# Function Signature

Tools should be asynchronous.

Example

```python
async def search_contacts(
    *,
    query: str,
    contact_service: ContactService,
) -> list[Contact]:
```

Always use keyword-only arguments.

---

# Dependency Injection

Dependencies should be passed into the tool.

Example

```python
company_service: CompanyService
```

Never instantiate services inside the tool.

---

# Business Logic

Business logic belongs inside services.

Tools should orchestrate existing services.

Good

```python
results = await contact_service.search(query)
```

Bad

```
SQL queries

Database sessions

Embedding generation

inside the tool
```

---

# Input Validation

Validate inputs before calling services.

Example

```python
if not query.strip():
    raise ValueError(
        "Query cannot be empty."
    )
```

Reject invalid requests early.

---

# Return Values

Return structured objects.

Examples

```
ORM models

Pydantic models

Dataclasses

Typed dictionaries
```

Avoid returning raw JSON strings.

---

# Error Handling

Allow domain exceptions to propagate.

Wrap unexpected failures only when adding meaningful context.

Good

```python
raise ToolExecutionError(...)
```

Avoid swallowing exceptions.

---

# Multi-tenancy

Always operate within the authenticated tenant.

Never expose data from another tenant.

Rely on tenant-aware services.

---

# Async

Every public tool should be asynchronous.

Example

```python
async def create_task(...):
```

Never block the event loop.

---

# Naming

File

```
create_task.py
```

Function

```python
create_task()
```

Keep names short and descriptive.

---

# Documentation

Each tool should include

- module docstring
- function docstring

Describe what the tool does and when it should be used.

---

# Logging

Only log important events.

Avoid excessive debug logging.

---

# Output Requirements

Generated code should include

- imports
- module documentation
- async function
- dependency injection
- validation
- type hints
- docstrings

No placeholders.

No TODO comments.

No SQL queries.

---

# Existing CRM Copilot Pattern

Example tools

Knowledge Search

- calls RetrievalService

Search Contacts

- calls ContactService

Create Task

- calls TaskService

Update Opportunity

- calls OpportunityService

Follow the same architecture.

---

# Code Style

Preferred

```python
results = await contact_service.search(
    query=query,
)

return results
```

Avoid nested conditionals.

Keep tools focused on one operation.

---

# Validation Checklist

Before finishing verify

- Single responsibility
- Async function
- Dependency injection
- No SQL queries
- Uses services
- Tenant-safe
- Input validation
- Proper error handling
- Type hints
- Production-ready implementation
```