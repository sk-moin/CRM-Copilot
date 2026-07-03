# Decision – Multi‑tenancy strategy

**Scope**: This decision
 documents how the codebase enforces tenant isolation and where the responsibility for validating cross‑model tenant ownership lies.

- `BaseRepository` provides generic, tenant‑scoped CRUD operations using the
  `tenant_scoped_query` helper. It **does not** validate that foreign‑key
  values (e.g. a `User.org_id`) belong to the same tenant as the repository’s
  `tenant_id`.

- Validation of such cross‑model relationships (ensuring that an `org_id`
  references an `Organization` whose `tenant_id` matches the current tenant,
  or that a `tenant_id` field cannot be altered to point to a different
  tenant) is deliberately deferred to the **service / use‑case layer** introduced
  in **spec 002**. Those higher‑level components will enforce the business rule
  before invoking the repository.

- This decision is recorded so that future contributors are aware that the
  repository is intentionally thin and that **additional checks must be added**
  in the service layer before any write endpoint is exposed.

*Reference*: `packages/database/repositories/base_repository.py` – generic CRUD
implementation; `packages/database/queries/tenant_scoped.py` – tenant‑scoped
query construction.
