# Session 000 – Foundations (Spec 000)

**Date:** 2026-06-13 – 2026-06-14  
**Goal:** Establish the database schema for Tenant → Organization → User, plus tenant-scoped query infrastructure.

---

## What was built

| Component | Files | Purpose |
|-----------|-------|---------|
| **SQLAlchemy Base** | `packages/database/models/base.py` | Declarative base for all ORM models. |
| **Models** | `tenant.py`, `organization.py`, `user.py` | Core entities with UUID PKs, timestamps, relationships, and `user_role` enum. |
| **Model exports** | `packages/database/models/__init__.py` | Re-exports `Base`, `Tenant`, `Organization`, `User` for convenient imports. |
| **Tenant-scoped query helper** | `packages/database/queries/tenant_scoped.py` | Builds `select()` that filters by `tenant_id` (direct or via `Organization`). |
| **Base repository** | `packages/database/repositories/base_repository.py` | Generic async CRUD using `tenant_scoped_query`; returns `None`/`False` for out-of-tenant rows. |
| **Alembic migration** | `alembic/versions/a8617753f0e8_...` | Creates `pgcrypto`, `vector` extensions, tables, indexes, and `user_role` enum. Downgrade drops tables/enum, keeps extensions. |
| **Docker Compose** | `docker-compose.yml` | `postgres` service using `pgvector/pgvector:pg16` on port 5433. |
| **Test fixtures** | `tests/conftest.py` | Per-test engine/fresh transaction pattern with rollback isolation. |
| **Unit test** | `tests/unit/database/test_models.py` | Creates Tenant/Org/User; verifies ORM relationships. |
| **Adversarial test** | `tests/adversarial/test_tenant_isolation.py` | Creates two tenants; confirms `BaseRepository` cannot access the other tenant’s data. |
| **Decision log** | `docs/decisions/004-multi-tenancy-strategy.md` | Documents that cross-model tenant ownership validation is deferred to the service layer. |

---

## Key decisions made

1. **Enum handling** – Let `CREATE TABLE` auto-create the `user_role` enum via the column definition; added explicit `DROP TYPE IF EXISTS` in downgrade.
2. **Transaction strategy in tests** – Fresh async engine + single transaction (`await conn.begin()`) per test, rolled back via `await conn.rollback()`; engine disposed afterward to avoid loop-pool conflicts.
3. **Repository design** – Returns `None`/`False` for out-of-tenant accesses (no `NotFoundError`), leaving 404 logic to the API layer.
4. **Docker image** – Used `pgvector/pgvector:pg16` so the `vector` extension is available without extra init scripts.
5. **DB URL configuration** – Migration now reads `DATABASE_URL` from the environment; `alembic.ini` is left empty to enforce this.

---

## Bugs encountered & fixes

| Bug | Symptom | Fix |
|-----|---------|-----|
| **Enum duplicate object (`DuplicateObject: type "user_role" already exists`)** | Migration tried to create enum twice (explicit create + implicit via column). | Removed explicit enum creation; let `CREATE TABLE` handle it; added `DROP TYPE IF EXISTS` in downgrade. |
| **Docker daemon not running** | `docker compose up` failed: “cannot connect to docker engine”. | Started Docker Desktop manually; re-ran compose command. |
| **Port 5432 conflict with local Postgres** | Migration or tests couldn’t bind to 5432 because another Postgres was running. | Changed Docker Compose port mapping to `5433:5432`; updated URLs to use port 5433. |
| **Event loop is closed** (tests) | Second test failed: “Event loop is closed” / “Connection already in use”. | Moved engine creation inside the fixture; fresh engine per test; disposed engine after rollback. |
| **Fabricated test output (`X.XXs`)** | Placeholder output was shown in earlier traces. | Added Rule 9 to CLAUDE.md: “Never fabricate command output…” |

---

## Open items carried forward (to be addressed before Spec 001)

1. **DB URL in Alembic** – currently falls back to local; ensure CI/CD sets `DATABASE_URL`.
2. **README note** – remind developers to run `docker compose up -d` before tests.
3. **Consider typed repository subclasses** (`TenantRepository`, `OrganizationRepository`) to avoid inline `UserRepository` pattern in adversarial test.
4. **Future: add `.env` support** – for local dev secrets (not committed).

---

**Status:** ✅ All acceptance criteria from Spec 000 are met (migration runs, tests pass, tenant isolation verified). Ready to proceed with Spec 001 (auth/JWT).