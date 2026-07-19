---
name: create-repository
description: Create a repository following the CRM Copilot repository pattern with multi-tenancy, SQLAlchemy 2.0, and BaseRepository conventions.
---

# Create Repository

## Goal

Implement a repository for a SQLAlchemy model following the CRM Copilot architecture.

Repositories should contain **database access only** and must not contain business logic.

---

# Responsibilities

This skill is responsible for:

- Creating repository classes
- Implementing CRUD operations
- Tenant-scoped queries
- Search and filtering
- Pagination support
- Database persistence
- Query optimization

This skill is NOT responsible for:

- Business rules
- Validation
- API schemas
- HTTP responses
- Service layer logic

---

# Project Structure

Repositories are located in:

packages/database/repositories/

Example

```
company_repository.py
contact_repository.py
task_repository.py
retrieval_trace_repository.py
```

---

# Base Repository

Unless explicitly instructed otherwise, every repository must inherit from

```python
BaseRepository
```

Example

```python
class CompanyRepository(
    BaseRepository[Company],
):
```

---

# Constructor

Repositories receive

```python
AsyncSession
tenant_id
```

Example

```python
def __init__(
    self,
    session: AsyncSession,
    tenant_id: UUID,
):
    super().__init__(
        session=session,
        tenant_id=tenant_id,
        model=Company,
    )
```

---

# Multi-tenancy

Every query must automatically respect tenant boundaries.

Never return data from another tenant.

Use BaseRepository tenant-scoping helpers whenever possible.

Never bypass tenant filtering.

---

# Async Only

Repositories must use

```python
AsyncSession
```

Never use synchronous SQLAlchemy APIs.

---

# CRUD Operations

Implement when appropriate

- create()
- get_by_id()
- update()
- delete()
- list()

Reuse BaseRepository methods whenever available.

Avoid duplicating functionality.

---

# Query Style

Use SQLAlchemy 2.0 syntax.

Example

```python
stmt = (
    select(Company)
    .where(...)
)
```

Avoid legacy Query APIs.

---

# Relationships

Use

```python
selectinload()
```

when loading relationships.

Avoid unnecessary lazy loading.

---

# Searching

If search is required

Prefer

```python
ilike()
```

or PostgreSQL full-text search when appropriate.

---

# Pagination

Use

```python
offset()

limit()
```

or project-standard pagination helpers.

Do not implement custom pagination logic.

---

# Transactions

Repositories should

```python
add()

flush()

refresh()
```

Commit should normally be handled by the service layer or request lifecycle unless the project convention specifies otherwise.

---

# Exceptions

Do not convert database exceptions into HTTP exceptions.

Allow service layer to decide.

---

# Type Hints

All public methods must include type hints.

Example

```python
async def get_by_id(
    self,
    id: UUID,
) -> Company | None:
```

---

# Naming

Repository

```python
CompanyRepository
```

Model

```python
Company
```

Methods

```python
get_by_id()

get_by_email()

get_active()

list()

search()
```

---

# Documentation

Repository should include

- class docstring
- method docstrings

Keep them concise.

---

# Output Requirements

Generated repository must include

- imports
- repository class
- constructor
- CRUD methods
- custom query methods
- type hints
- docstrings

No placeholders.

No TODO comments.

No business logic.

---

# Validation Checklist

Before finishing verify

- Inherits from BaseRepository
- Uses AsyncSession
- Uses SQLAlchemy 2.0
- Tenant-scoped
- No business logic
- Correct imports
- Type hints present
- Production-ready implementation