---
name: create-service
description: Create a service following the CRM Copilot service layer architecture. Services contain business logic, coordinate repositories, enforce authorization, and remain independent of HTTP or database implementation details.
---

# Create Service

## Goal

Implement a production-ready service following the CRM Copilot architecture.

Services are responsible for business logic and orchestration. They coordinate repositories, validate business rules, perform authorization checks, and return domain objects.

---

# Responsibilities

This skill is responsible for:

- Business logic
- Repository orchestration
- Authorization
- Validation
- Transaction coordination
- Audit logging (when applicable)
- Returning domain objects

This skill is NOT responsible for:

- SQL queries
- HTTP responses
- FastAPI routing
- Request validation
- Pydantic schemas
- Dependency injection

---

# Project Structure

Services are located in

```
app/services/
```

Examples

```
company_service.py
contact_service.py
task_service.py
audit_service.py
chat_service.py
retrieval_trace_service.py
retrieved_chunk_service.py
```

---

# Constructor

Every service should receive its dependencies through constructor injection.

Typical constructor

```python
def __init__(
    self,
    *,
    session: AsyncSession,
    current_user: User,
):
```

or

```python
def __init__(
    self,
    repository: CompanyRepository,
):
```

Do not instantiate repositories inside methods.

---

# Business Logic

Business rules belong in the service.

Examples

- duplicate detection
- ownership checks
- permission checks
- workflow validation
- status transitions
- audit recording

Repositories should never contain business rules.

---

# Repository Usage

Services coordinate one or more repositories.

Example

```
CompanyRepository

ContactRepository

TaskRepository
```

The service decides which repositories are needed.

---

# Authorization

Whenever required

Verify that the authenticated user has permission to perform the operation.

Examples

- tenant ownership
- organization ownership
- role checks
- resource ownership

Never trust client input.

---

# Multi-tenancy

Always operate within the authenticated tenant.

Never expose another tenant's data.

Use the repositories' tenant-aware filtering.

---

# Transactions

The service coordinates transactions.

Typical operations

```python
create()

update()

delete()
```

Repositories should not implement workflow logic.

---

# Validation

Validate business rules before persisting data.

Examples

- duplicate emails
- invalid state transitions
- inactive entities
- missing dependencies

Raise domain exceptions when validation fails.

---

# Exceptions

Raise domain-specific exceptions.

Do not raise

```
HTTPException
```

Do not return HTTP responses.

Those belong to the API layer.

---

# Return Values

Return

- ORM models
- domain objects
- DTOs used internally

Do not return JSON dictionaries.

Do not return FastAPI Response objects.

---

# Async

All public methods should be asynchronous.

Example

```python
async def create(...)
```

Use AsyncSession throughout.

---

# Logging

Only perform logging when required.

Avoid excessive logging inside simple CRUD operations.

---

# Naming

Service

```
CompanyService
```

Methods

```
create_company()

update_company()

delete_company()

get_company()

list_companies()
```

Use descriptive names.

---

# Documentation

Every service should include

- class docstring
- method docstrings

Describe business responsibility instead of implementation details.

---

# Output Requirements

Generated code should include

- imports
- service class
- constructor
- business methods
- validation
- authorization
- type hints
- docstrings

No placeholders.

No TODO comments.

No SQL queries.

---

# Code Style

Prefer

```python
if company is None:
    raise ...
```

over deeply nested conditionals.

Keep methods focused on one business operation.

Extract repeated logic into private helper methods.

---

# Validation Checklist

Before finishing verify

- Business logic only
- No SQL queries
- No FastAPI imports
- No HTTPException
- Repository orchestration
- Authorization implemented
- Tenant-safe
- Async methods
- Proper type hints
- Production-ready implementation