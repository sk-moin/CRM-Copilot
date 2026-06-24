# Spec 000 — Foundations: DB Models, Migrations, Tenant Scoping

## Goal

Establish the database schema for Tenant -> Organization -> User, plus the
tenant-scoped query infrastructure that every later spec depends on. Nothing
in this spec touches the API layer or AI layer — pure data foundation.

## Why this spec is first

Every other module assumes (a) the models exist, (b) tenant_id propagation
works, and (c) there's a tested, reusable way to enforce tenant isolation
in queries. Getting this wrong is the hardest class of bug to fix later
(potential data leak across tenants), so it gets the most scrutiny now.

## Scope

### In scope
- SQLAlchemy 2.x async models: `Tenant`, `Organization`, `User`
- Alembic setup + first migration creating these tables
- `BaseRepository` with a tenant-scoped query helper
- `TenantScopedQuery` mixin/utility in `packages/database/queries/tenant_scoped.py`
- Local Postgres via docker-compose for dev
- Adversarial test: attempt cross-tenant read, assert it returns nothing

### Out of scope (later specs)
- Company/Contact/Opportunity/Task/Note models → spec 002
- Auth/JWT/password hashing → spec 001
- Audit log, activity timeline → spec 003
- Vector document model → spec 004

## Data model

### Tenant
| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | default `gen_random_uuid()` |
| name | string, not null | |
| subdomain | string, unique, not null | lowercase, indexed |
| created_at | timestamptz | default now() |

### Organization
| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| tenant_id | UUID, FK -> tenant.id, not null, indexed | |
| name | string, not null | |
| domain | string, nullable | |
| created_at | timestamptz | default now() |

### User
| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| org_id | UUID, FK -> organization.id, not null, indexed | |
| email | string, unique, not null, indexed | |
| password_hash | string, not null | bcrypt — hashing logic itself is spec 001, but column exists now |
| role | string, not null | enum-like: OWNER/ADMIN/MANAGER/MEMBER, default MEMBER |
| created_at | timestamptz | default now() |

**Note on tenant_id propagation**: `User` and everything below `Organization`
reaches `tenant_id` via `organization.tenant_id`, not a direct column.
`tenant_scoped.py` must handle this via a join, not assume every table has
a `tenant_id` column directly.

## Tenant-scoped query layer

`packages/database/queries/tenant_scoped.py` provides:

```python
async def tenant_scoped_query(session, model, tenant_id, **filters):
    """
    Returns a SQLAlchemy select() for `model`, automatically joined/filtered
    to the given tenant_id. Raises ValueError if `model` has no path to
    tenant_id (fail loud, not silent).
    """
```

`BaseRepository` (`packages/database/repositories/base_repository.py`):

```python
class BaseRepository:
    model: type
    def __init__(self, session: AsyncSession, tenant_id: UUID): ...
    async def get_by_id(self, id: UUID) -> Model | None: ...  # tenant-scoped
    async def list(self, **filters) -> list[Model]: ...        # tenant-scoped
    async def create(self, **data) -> Model: ...
    async def update(self, id: UUID, **data) -> Model | None: ...  # tenant-scoped
    async def delete(self, id: UUID) -> bool: ...               # tenant-scoped
```

Every method that takes an `id` must verify the row belongs to the
repository's `tenant_id` before returning/mutating it — not just filter
the list, but explicitly deny access to out-of-tenant IDs (return `None`
or raise `NotFoundError`, not a 403 — don't leak existence).

## Migrations

- Alembic initialized in `packages/database/migrations/`
- First migration: create `tenant`, `organization`, `user` tables with
  the columns above, plus indexes on `tenant.subdomain`, `organization.tenant_id`,
  `user.org_id`, `user.email`
- Migration must be reversible (`downgrade()` drops tables in correct order)

## docker-compose addition

Add a `postgres` service (postgres:16, with pgvector extension available
even though unused until spec 004 — install the extension in an init script
now so migration for spec 004 is trivial).

## Tests (`tests/`)

### `tests/unit/database/test_models.py`
- Create a Tenant, Organization, User — assert relationships resolve

### `tests/adversarial/test_tenant_isolation.py`
- Create two tenants (A, B), each with an org and a user
- Using `BaseRepository` scoped to tenant A, attempt `get_by_id()` on a
  user belonging to tenant B's org
- Assert result is `None` (not the actual user object)
- Attempt `list()` scoped to tenant A — assert tenant B's user is NOT
  in the results

## Acceptance criteria

- [ ] `alembic upgrade head` runs cleanly against local docker-compose postgres
- [ ] `alembic downgrade base` runs cleanly (reversible)
- [ ] All unit tests pass
- [ ] Adversarial isolation test passes
- [ ] `tenant_scoped_query` raises `ValueError` (not silent pass-through)
      if given a model with no path to tenant_id
- [ ] No raw SQL string concatenation anywhere in this module

## Open questions for me (ask before assuming)

- Naming convention: `org_id` vs `organization_id` — spec uses `org_id`,
  confirm before generating migration if codebase convention differs.
- UUID generation: DB-side (`gen_random_uuid()`, requires `pgcrypto`) vs
  application-side (Python `uuid4()`) — pick DB-side unless told otherwise,
  but flag it.