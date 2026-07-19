---
name: create-model
description: Create a new SQLAlchemy model following the CRM Copilot architecture and project conventions.
---

# Create SQLAlchemy Model

## Goal

Implement a new SQLAlchemy model that follows the existing architecture, coding standards, and multi-tenant design used throughout CRM Copilot.

The generated model must be production-ready and require minimal manual modification.

---

# Responsibilities

This skill is responsible for:

- Creating a SQLAlchemy ORM model
- Defining table name
- Adding columns
- Creating relationships
- Configuring UUID primary keys
- Adding timestamps
- Supporting multi-tenancy
- Following project naming conventions

This skill is **NOT** responsible for:

- Repository implementation
- Service implementation
- API endpoints
- Alembic migrations
- Business logic

---

# Project Architecture

Models are located in:

packages/database/models/

Example:

packages/database/models/company.py
packages/database/models/contact.py
packages/database/models/task.py

---

# Base Class

Every model must inherit from:

```python
Base
```

from

```python
packages.database.base
```

---

# Primary Key

Always use UUID.

Example

```python
id = mapped_column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
)
```

Never use integer IDs.

---

# Multi-tenancy

Unless explicitly told otherwise, every business entity must contain

```python
tenant_id
```

Example

```python
tenant_id = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("tenants.id"),
    nullable=False,
)
```

---

# Organization Scope

If the entity belongs to an organization, include

```python
org_id
```

Example

```python
org_id = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("organizations.id"),
    nullable=False,
)
```

---

# Audit Fields

Always include

```python
created_at

updated_at
```

Use the same implementation already used by existing models.

---

# Relationships

Use SQLAlchemy relationships.

Example

```python
company = relationship(
    "Company",
    back_populates="contacts",
)
```

Bidirectional relationships should always use

```python
back_populates
```

Avoid one-way relationships unless necessary.

---

# Enum Fields

If an enum exists

Use

```python
Enum(...)
```

Do not use string literals.

---

# Nullable Rules

Only mark nullable=True when appropriate.

Avoid unnecessary nullable columns.

---

# Naming Conventions

Classes

```text
Company
Contact
Opportunity
```

Table names

```text
companies
contacts
opportunities
```

Foreign Keys

```text
company_id
contact_id
task_id
```

Relationship names

Singular

```python
company
```

Plural

```python
contacts
```

---

# Type Hints

Use SQLAlchemy 2.0 typing.

Example

```python
name: Mapped[str]
```

Relationships

```python
contacts: Mapped[list["Contact"]]
```

---

# Imports

Prefer

```python
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
```

instead of wildcard imports.

---

# Documentation

Every model should include a concise class docstring describing its purpose.

Example

```python
"""
Represents a CRM company belonging to a tenant.
"""
```

---

# Output Requirements

Generated code should include

- imports
- table definition
- columns
- relationships
- timestamps
- docstrings
- type hints

No placeholders.

No TODO comments.

No pseudocode.

---

# Validation Checklist

Before finishing verify

- UUID primary key
- Correct table name
- Tenant support
- Organization support (if required)
- Relationships configured
- SQLAlchemy 2.0 typing
- Proper imports
- Clean formatting
- Production-ready implementation
