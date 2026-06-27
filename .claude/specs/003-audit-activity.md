# Spec 003 — Audit & Activity

## Goal

Implement a comprehensive audit and activity tracking system for CRM Copilot.

Every mutation on CRM entities must be recorded as an immutable audit event.

The system must support:

* Entity activity timelines
* User activity feeds
* Tenant-wide recent activity
* Future AI event tracking
* Future approval workflows
* Compliance and auditability requirements

This specification establishes the foundation for:

* Spec 007 — AI Agent
* Spec 008 — Prompt Management
* Spec 009 — Guardrails
* Spec 010 — Approval Layer

---

# Context

Architecture:

```text
FastAPI
    ↓
Router
    ↓
Service
    ↓
Repository
    ↓
Async SQLAlchemy
    ↓
PostgreSQL
```

Multi-tenancy:

```text
All queries MUST be tenant-scoped.
```

Current state:

```text
Spec 000 — Database Foundations     ✅
Spec 001 — Auth & RBAC              ✅
Spec 002 — CRM Core                 ✅

Current test count:
45 passing tests
0 failures
```

---

# High-Level Objectives

Implement:

1. Immutable audit log storage
2. Activity timelines per CRM entity
3. User activity feeds
4. Tenant-wide recent activity
5. Automatic CRM audit event generation
6. Future-ready AI event support

---

# Scope

## Included

* AuditLog model
* AuditRepository
* AuditService
* Audit API endpoints
* CRM service integration
* Audit migration
* Audit tests

## Not Included

* Real-time activity feeds
* WebSocket streaming
* Audit dashboards
* Audit retention policies
* AI event wiring
* READ-event tracking implementation

---

# Design Principles

## Immutability

Audit logs are append-only.

Audit logs must never be:

* updated
* deleted
* soft-deleted

through application code.

---

## Tenant Isolation

Every query must include:

```python
tenant_id
```

Cross-tenant access must be impossible.

---

## Extensibility

Audit schema must support future:

* AI prompts
* AI tool calls
* approvals
* human review workflows

without requiring database migrations.

---

# Phase Breakdown

## Phase 3A — Audit Model + Migration

Deliverables:

* AuditAction enum
* AuditLog model
* Alembic migration
* Database indexes

---

## Phase 3B — Repository Layer

Deliverables:

* AuditRepository
* Timeline queries
* User activity queries
* Tenant recent activity queries

---

## Phase 3C — Audit Service

Deliverables:

* AuditService
* Snapshot builders
* Audit event creation helpers

---

## Phase 3D — CRM Service Integration

Deliverables:

* Company audit hooks
* Contact audit hooks
* Opportunity audit hooks
* Task audit hooks
* Note audit hooks (if service exists)

---

## Phase 3E — Audit API

Deliverables:

* Timeline endpoint
* User activity endpoint
* Recent activity endpoint

---

## Phase 3F — Testing & Hardening

Deliverables:

* Unit tests
* Integration tests
* Adversarial tests
* Tenant isolation validation

---

# Data Model

## AuditAction Enum

File:

```text
app/models/audit.py
```

```python
from enum import Enum

class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    READ = "READ"

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"

    AI_PROMPT = "AI_PROMPT"
    AI_TOOL_CALL = "AI_TOOL_CALL"

    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
```

### Note

READ events are reserved for future compliance features.

READ tracking is NOT implemented in Spec 003.

---

## AuditLog Model

File:

```text
app/models/audit.py
```

```python
class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id"),
        nullable=False,
    )

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organization.id"),
        nullable=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True,
    )

    entity_type = Column(String(50), nullable=False)

    entity_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    action = Column(
        ENUM(AuditAction, name="audit_action"),
        nullable=False,
    )

    before_values = Column(JSON, nullable=True)

    after_values = Column(JSON, nullable=True)

    ip_address = Column(String(45), nullable=True)

    user_agent = Column(String(255), nullable=True)

    event_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_audit_logs_tenant_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_audit_logs_tenant_user",
            "tenant_id",
            "user_id",
        ),
        Index(
            "ix_audit_logs_created_at",
            "created_at",
        ),
    )
```

---

# Important Model Rules

## entity_id

No foreign key.

Reason:

```text
Polymorphic reference.
```

Can point to:

* Company
* Contact
* Opportunity
* Task
* Note

---

## event_metadata

Use:

```python
event_metadata
```

Do NOT use:

```python
metadata
```

because SQLAlchemy reserves that attribute internally.

---

## org_id

Must be populated whenever available.

This supports future:

```text
Tenant
    ├── Organization A
    ├── Organization B
    └── Organization C
```

structures.

---

# Repository Layer

File:

```text
app/repositories/audit.py
```

---

## AuditRepository

Inherits:

```python
BaseRepository[AuditLog]
```

---

## Required Methods

### get_by_entity

```python
async def get_by_entity(
    tenant_id,
    entity_type,
    entity_id,
    limit=50,
    offset=0,
)
```

Returns:

```text
Entity timeline
```

Order:

```text
created_at DESC
```

---

### get_by_user

```python
async def get_by_user(
    tenant_id,
    user_id,
    limit=50,
)
```

Returns:

```text
User activity feed
```

---

### get_recent_by_tenant

```python
async def get_recent_by_tenant(
    tenant_id,
    actions=None,
    limit=100,
)
```

Returns:

```text
Recent tenant activity
```

---

## Immutability Enforcement

AuditRepository must override:

```python
update()
delete()
```

and raise:

```python
NotImplementedError
```

---

# Service Layer

File:

```text
app/services/audit.py
```

---

## Constructor

```python
def __init__(
    self,
    session: AsyncSession,
    current_user: Optional[Any] = None,
)
```

---

## Snapshot Helpers

Required:

```python
build_company_snapshot()
build_contact_snapshot()
build_opportunity_snapshot()
build_task_snapshot()
```

or equivalent helper architecture.

Purpose:

```text
Prevent duplicate snapshot code across services.
```

---

## Central Method

```python
async def log_event(
    action,
    entity_type,
    entity_id,
    tenant_id,
    org_id=None,
    before_values=None,
    after_values=None,
    event_metadata=None,
    ip_address=None,
    user_agent=None,
)
```

---

## Convenience Methods

```python
log_create()
log_update()
log_delete()
```

---

## User Resolution

If current_user exists:

```python
user_id = current_user.id
```

Otherwise:

```python
user_id = None
```

Supports:

* system actions
* AI actions

---

## Framework Independence

Do NOT pass FastAPI Request objects into services.

Use:

```python
ip_address
user_agent
```

instead.

This preserves:

```text
Router → Service separation
```

introduced in Spec 002.

---

# CRM Integration

Modify:

```text
app/services/company_service.py
app/services/contact_service.py
app/services/opportunity_service.py
app/services/task_service.py
```

---

## Constructor

Add:

```python
self.audit = AuditService(
    session,
    current_user,
)
```

---

## Create

Emit:

```python
await self.audit.log_create(...)
```

after successful persistence.

---

## Update

Emit:

```python
await self.audit.log_update(...)
```

with:

```python
before_values
after_values
```

---

## Delete

Emit:

```python
await self.audit.log_delete(...)
```

with:

```python
before_values
```

---

## Snapshot Rules

Only include meaningful fields.

Do NOT serialize entire ORM objects.

Example:

```python
{
    "name": company.name,
    "industry": company.industry,
    "website": company.website,
}
```

---

# API Layer

## Schemas

File:

```text
app/api/schemas/audit.py
```

Create:

```python
AuditLogResponse
ActivityTimelineResponse
```

---

## Timeline Response

```python
class ActivityTimelineResponse(BaseModel):
    entity_type: str
    entity_id: UUID
    events: list[AuditLogResponse]
    count: int
```

Use:

```python
count
```

instead of:

```python
total
```

until full pagination metadata exists.

---

# Router

File:

```text
app/api/routers/audit.py
```

Endpoints:

```http
GET /audit/timeline/{entity_type}/{entity_id}

GET /audit/user/{user_id}

GET /audit/recent
```

---

# Dependency Injection

Modify:

```text
app/api/dependencies.py
```

Add:

```python
get_audit_service()
```

---

# Migration

Create:

```bash
alembic revision -m "add audit_logs table"
```

Migration must:

* create audit_action enum
* create audit_logs table
* create indexes
* create FK constraints

No FK on:

```python
entity_id
```

---

# Testing Requirements

## Unit Tests

AuditLog model:

* action enum validation
* tenant_id required
* entity_type required
* entity_id required

AuditRepository:

* get_by_entity
* get_by_user
* get_recent_by_tenant

AuditService:

* log_event
* log_create
* log_update
* log_delete

---

## Integration Tests

Verify:

* Company CREATE creates audit event
* Contact UPDATE creates audit event
* Opportunity DELETE creates audit event
* Task CREATE creates audit event

Verify:

* action
* tenant_id
* entity_type
* entity_id

---

## Adversarial Tests

Verify:

* no cross-tenant visibility
* no tenant leakage
* immutable audit records

---

# Target Test Count

Current:

```text
45 passing tests
```

Target:

```text
60+ passing tests
```

Minimum:

```text
15 new tests
```

---

# Files To Create

```text
app/models/audit.py

app/repositories/audit.py

app/services/audit.py

app/api/schemas/audit.py

app/api/routers/audit.py

alembic/versions/xxx_add_audit_logs_table.py
```

---

# Files To Modify

```text
app/api/dependencies.py

app/services/company_service.py

app/services/contact_service.py

app/services/opportunity_service.py

app/services/task_service.py

app/services/note_service.py
    (if exists)

app/main.py
or
app/api/router.py

tests/
```

---

# Acceptance Criteria

* AuditLog model exists
* Migration succeeds
* AuditRepository implemented
* AuditService implemented
* CRM services emit audit events
* Before/after snapshots meaningful
* Timeline endpoint works
* User activity endpoint works
* Recent activity endpoint works
* Tenant isolation enforced
* 60+ tests passing
* Original 45 tests still passing
* Audit logs cannot be updated
* Audit logs cannot be deleted

---

# Out of Scope

Future specs will handle:

* AI prompt tracking
* AI tool call tracking
* approval workflows
* real-time activity feeds
* audit dashboards
* retention policies
* READ-event logging

The schema introduced in Spec 003 must support those future capabilities without requiring additional database migrations.
