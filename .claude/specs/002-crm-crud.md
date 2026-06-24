# Spec 002 — CRM Core CRUD

## Goal
Implement core Customer Relationship Management (CRM) functionality that includes:
- **Companies**
- **Contacts**
- **Opportunities**
- **Tasks**
- **Notes**

These entities will support multi‑tenant isolation and follow the project's established patterns.

## Scope

### Companies
- CRUD operations
- Fields:
  - `name` (string, required)
  - `industry` (string, optional)
  - `website` (string, optional)
  - `phone` (string, optional)
  - `email` (string, optional)
  - `address` (string, optional)

### Contacts
- CRUD operations
- Association to a **Company**
- Fields:
  - `first_name` (string)
  - `last_name` (string)
  - `email` (string)
  - `phone` (string)
  - `job_title` (string)

### Opportunities
- CRUD operations
- Sales pipeline tracking
- Fields:
  - `title` (string)
  - `company_id` (FK → `companies.id`)
  - `owner_user_id` (FK → `users.id`)
  - `stage` (enum)
  - `probability` (integer 0‑100)
  - `value` (numeric)
  - `expected_close_date` (date)
- Stages:
  - `LEAD`
  - `QUALIFIED`
  - `PROPOSAL`
  - `NEGOTIATION`
  - `WON`
  - `LOST`

### Tasks
- CRUD operations
- Assignment to users **and** optional attachment to CRM entities
- Fields:
  - `title` (string)
  - `description` (string, optional)
  - `status` (enum: `PENDING`, `IN_PROGRESS`, `COMPLETED`)
  - `priority` (enum: `LOW`, `MEDIUM`, `HIGH`)
  - `due_date` (ISO 8601 date string, optional)
  - `assigned_to_user_id` (UUID referencing a user)
  - `entity_type` (enum: `company`, `contact`, `opportunity`, optional)
  - `entity_id` (UUID referencing the parent entity, optional)

### Notes
- Attachable to any CRM entity (Company, Contact, Opportunity)
- Polymorphic design:
  - `entity_type` (string, one of `company`, `contact`, `opportunity`)
  - `entity_id` (UUID referencing the parent entity)
- **Validation requirements** (service layer):
  - `entity_type` must be one of the allowed values.
  - Referenced entity must exist.
  - Referenced entity must belong to the same tenant as the note.

## Architecture Requirements
Implementation must adhere to existing project patterns:

| Layer | Location |
|-------|----------|
| **Models** | `packages/database/models/` |
| **Repositories** | `packages/database/repositories/` |
| **Services** | `packages/crm/services/` |
| **API Routing** | `apps/api/routers/` |

All database access must go through the repository pattern established in Spec 000.

## Repository Requirements
- Repositories to provide:
  - `CompanyRepository`
  - `ContactRepository`
  - `OpportunityRepository`
  - `TaskRepository`
  - `NoteRepository`
- All methods must require `tenant_id` and enforce tenant scoping.
- No cross‑tenant access is permitted.
- Follow the tenant‑scoped repository pattern from Spec 000.
- CRUD operations must be tenant‑safe by default.

## Service Layer Responsibilities
Services are responsible for:
- Validation of input data.
- Business rules enforcement.
- Ownership and relationship checks.
- Tenant enforcement for every operation.
- Permission enforcement based on RBAC.
- Existence checks for related entities, e.g.:
  - Contact must belong to an existing company.
  - Opportunity must belong to an existing company.
  - Assigned user must exist within the tenant.
  - Notes cannot attach across tenants.

## Multi‑Tenancy Requirements
CRM entities must follow the tenant-scoping architecture established in Spec 000.

Tenant isolation is enforced through:

- Direct tenant_id columns, or
- Direct org_id columns that resolve to Organization.tenant_id

The current repository infrastructure (BaseRepository + tenant_scoped_query) only supports these patterns.

For CRM entities, tenant ownership will be resolved through org_id.

Requirements:

- Every CRM table must contain org_id.
- org_id must reference organization.id.
- Every repository query must be tenant scoped through the existing tenant_scoped_query helper.
- Cross-tenant access is strictly forbidden.
- No repository may bypass tenant scoping.

## Database Changes
New tables:

| Table | Key Columns & Constraints |
|-------|----------------------------|
| **companies** | `id` PK, `org_id` FK → `organization.id`, `name`, `industry`, `website`, `phone`, `email`, `address` `created_at`, `updated_at` |
| **contacts** | `id` PK, `org_id` FK → `organization.id`, `company_id` FK → `companies.id`, `first_name`, `last_name`, `email`, `phone`, `job_title`, `created_at`, `updated_at` |
| **opportunities** | `id` PK, `org_id` FK → `organization.id`, `title`, `company_id` FK → `companies.id`, `owner_user_id` FK → `users.id`, `stage` (enum), `probability` (int), `value` (numeric), `expected_close_date` (date), `created_at`, `updated_at` |
| **tasks** | `id` PK, `org_id` FK → `organization.id`, `entity_type` (enum), `entity_id` (UUID), `title`, `description`, `status` (enum), `priority` (enum), `due_date`, `assigned_to_user_id` (FK → `users.id`), `created_at`, `updated_at` |
| **notes** | `id` PK, `org_id` FK → `organization.id`, `entity_type` (enum), `entity_id` (UUID), `content`, `created_at`, `updated_at` |

- **Foreign keys** enforced for relational integrity.
- **Indexes** (see Index Strategy below).
- **Timestamps** (`created_at`, `updated_at`) automatically managed.
- **Relationships** defined per repository layer.

Relationships:

Tenant
└── Organization
├── Users
├── Companies
│ ├── Contacts
│ └── Opportunities
├── Tasks
└── Notes

## Index Strategy
| Entity | Recommended Indexes |
|--------|--------------------|
| **companies** | `org_id`, `(org_id, name)` |
| **contacts** | `org_id`, `(org_id, company_id)`, `(org_id, email)` |
| **opportunities** | `org_id`, `(org_id, company_id)`, `(org_id, stage)` |
| **tasks** | `org_id`, `(org_id, assigned_to_user_id)` |
| **notes** | `org_id`, `(org_id, entity_type, entity_id)` |


## Architectural Constraint

Spec 002 must remain compatible with the tenant isolation framework introduced in Spec 000.

No changes to:

- BaseRepository
- tenant_scoped_query
- authentication tenant resolution

should be required to implement CRM entities.

CRM models must therefore expose a direct `org_id` column so they can participate in existing tenant-scoped repository behavior.

## Querying & Filtering
Support common filter parameters in API endpoints (pagination may be added later):
- **Companies**: search by `name`.
- **Contacts**: filter by `company_id`.
- **Opportunities**: filter by `stage` and `company_id`.
- **Tasks**: filter by `status` and `assigned_to_user_id`.
- **Notes**: filter by `entity_type` and `entity_id`.

## API Scope
Endpoints (RESTful) to be implemented under `apps/api/routers/`:

### Companies
- `POST /companies`
- `GET /companies`
- `GET /companies/{id}`
- `PATCH /companies/{id}`
- `DELETE /companies/{id}`

### Contacts
- `POST /contacts`
- `GET /contacts`
- `GET /contacts/{id}`
- `PATCH /contacts/{id}`
- `DELETE /contacts/{id}`

### Opportunities
- `POST /opportunities`
- `GET /opportunities`
- `GET /opportunities/{id}`
- `PATCH /opportunities/{id}`
- `DELETE /opportunities/{id}`

### Tasks
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{id}`
- `PATCH /tasks/{id}`
- `DELETE /tasks/{id}`

### Notes
- `POST /notes`
- `GET /notes`
- `DELETE /notes/{id}`

All endpoints must enforce tenant scoping and authentication/authorization as per existing patterns.

## Testing Requirements
- **CRUD tests** for each entity, verifying success and error paths.
- **Tenant isolation tests** ensuring no cross‑tenant data leakage.
- **Auth dependency tests** confirming proper permission checks.
- **Relationship tests** validating foreign key constraints and polymorphic note attachment.
- **Permission tests** where applicable (e.g., role‑based access control).

## Implementation Plan
**Phase 2A — Models**
- ORM models with fields, enums, constraints, and relationships.

**Phase 2B — Database Migration**
- Alembic migration scripts creating tables, foreign keys, and indexes.

**Phase 2C — Repositories**
- Tenant‑scoped CRUD repositories for each entity.

**Phase 2D — Services**
- Business logic, validation, ownership, and tenant enforcement.

**Phase 2E — API Routers**
- CRUD endpoints with auth integration and filtering support.

**Phase 2F — Tests**
- Comprehensive test suite covering CRUD, tenant isolation, relationships, and permissions.

## Completion Criteria
Spec 002 is considered complete when:
1. Database migrations pass without errors.
2. Models, repositories, services, and API routers are fully implemented.
3. End‑to‑end tests for CRUD operations, tenant isolation, relationships, and auth succeed.
4. The sessional specification document has been created and reviewed.
5. All changes are committed to the repository.

--- 