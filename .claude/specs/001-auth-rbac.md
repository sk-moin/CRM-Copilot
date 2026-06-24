# Spec 001 — Auth & RBAC

## Goal
Provide a secure, tenant‑aware authentication and authorization layer for the CRM Copilot API.  All auth‑related endpoints must enforce tenant isolation, issue short‑lived JWT access tokens, and manage rotating refresh tokens stored in Redis.

## Scope
- **Endpoints**
  - `POST /auth/register` – create a new user (tenant & organization context)  
    *Registration Flow* (see section below)
  - `POST /auth/login` – exchange credentials for an access token & refresh token
  - `GET  /auth/me` – return the current user profile (requires a valid access token)
  - `POST /auth/refresh` – rotate the refresh token and issue a new access token

- **JWT (access token)**
  - Lifetime: **15 minutes**
  - **Mandatory claims**
    - `sub` – the user’s UUID (`user_id`)
    - `jti` – unique token identifier (UUID4)
    - `tenant_id` – UUID of the tenant the user belongs to
    - `org_id` – UUID of the organization the user belongs to
    - `role` – RBAC role string (`OWNER`, `ADMIN`, `MANAGER`, `MEMBER`)
    - `iss` – issuer (e.g. `crm-copilot.auth`)
    - `aud` – audience (e.g. `crm-copilot.api`)
    - `iat` – issued‑at timestamp
    - `exp` – expiration timestamp (15 min after `iat`)
  - Signed with **HS256** using a secret stored in the environment (`JWT_SECRET`).

- **Refresh tokens**
  - **Opaque random tokens** stored in Redis (Upstash/Redis Cloud) with a TTL of **30 days**.
  - **Redis key format:** `refresh:{token_hash}` – only a **hash of the refresh token** is stored.
  - **Redis value (JSON):**
    ```json
    {
      "user_id": "<UUID>",
      "tenant_id": "<UUID>",
      "org_id": "<UUID>",
      "role": "<ROLE>"
    }
    ```
  - **During refresh:**
    1. Hash the presented token.
    2. Look up `refresh:{token_hash}`.
    3. Validate that the key exists.
    4. Rotate by **deleting the old key** and creating a **new key** with a freshly generated opaque token (store its hash).
  - *Note:* Storing only the hash protects the token value if Redis is ever compromised, because the raw token never leaves the client side.

- **Security**
  - Password hashing: **passlib[bcrypt]** (`bcrypt_sha256` recommended) – store only the hash in `password_hash`.
  - JWT handling: **python‑jose[cryptography]** for encoding/decoding/verification.
  - All endpoints must run through the **fastapi‑limiter** middleware (see Rate Limiting).

- **Rate limiting**
  - `POST /auth/register` – **5 requests per minute per IP**.
  - `POST /auth/login` – **5 requests per minute per IP**.
  - Limits enforced via Redis‑backed `fastapi‑limiter`.

- **Repositories** (`packages/database/repositories/`)
  - `UserRepository` – create, get by email, get by id, update password.
  - `OrganizationRepository` responsibilities:
    * create organization
    * validate subdomain uniqueness
    * retrieve organization metadata
    Registration must validate uniqueness before creating records.
  - All repository methods must use the **tenant‑scoped query helper** from `BaseRepository`; passing `tenant_id=None` must raise an error.

- **Registration Flow**
  1. **Create Tenant** – insert a new `Tenant` record.
  2. **Create Default Organization** – linked to the newly created tenant.
  3. **Create Owner User** – linked to the organization, with a bcrypt‑hashed password and role `OWNER`.

  The three steps must execute inside a **single database transaction**.  If any step fails, the transaction **rolls back** so that **no partial records remain**.

- **Profile payload**
  ```json
  {
    "id": "<user UUID>",
    "email": "<email>",
    "role": "<role>",
    "org_id": "<organization UUID>",
    "tenant_id": "<tenant UUID>",
    "created_at": "<ISO‑8601 timestamp>"
  }
  ```
  *created_at is populated from the database `User.created_at` column.*

- **Error types**
  - `DuplicateEmailError` – raised when trying to register with an email that already exists in the **system**.
  - `DuplicateSubdomainError` – raised if the organization’s subdomain already exists.
  - `InvalidCredentialsError` – raised on login when email/password do not match.
  - `UserNotFoundError` – raised when a token refers to a non‑existent user (e.g., stale token).

## Multi-Tenant Isolation
- Tenant‑scoped repositories **require** `tenant_id`; they must not operate without it.
- Supplying `tenant_id=None` raises **InvalidTenantIdError**.
- Cross‑tenant access must **never succeed**; attempts should yield `None` or raise an appropriate error.
- The JWT’s `tenant_id` claim **must match** the repository’s tenant context for every request.
- All authenticated requests operate within a **resolved tenant context** derived from the JWT.
- Tenant isolation is a **non‑negotiable architectural constraint**.

## RBAC Roles

### OWNER
* Full tenant access
* Manage billing
* Manage users
* Manage organizations
* Manage CRM resources

### ADMIN
* Manage users
* Manage CRM resources
* Cannot transfer tenant ownership

### MANAGER
* Manage assigned records
* Manage team‑owned resources

### MEMBER
* Standard CRM access
* Access only authorized resources

*Note:* Detailed permission matrices will be expanded in a future authorization specification if required.

## Audit logging
- Deferred to **Spec 003**. No audit calls should be added here.

## Acceptance Criteria
- [ ] All four endpoints return appropriate HTTP status codes (201 for register, 200 for login/me/refresh, 400/401/429 on errors/limits).
- [ ] Access token validates correctly; includes all required claims.
- [ ] Refresh token rotation invalidates previous token and issues a new one.
- [ ] Refresh tokens are **single‑use**; reusing a rotated token returns **HTTP 401**.
- [ ] Passwords are stored only as bcrypt hashes; plain passwords never persisted.
- [ ] Rate limiting blocks excess calls with `429 Too Many Requests`.
- [ ] Repository methods reject `tenant_id=None` and enforce tenant filtering.
- [ ] Registration flow executes in a single transaction; failures leave no partial data.
- [ ] Unit tests for each endpoint cover happy path, duplicate email/subdomain, invalid credentials, token expiration, and refresh rotation.
- [ ] Adversarial tests verify that a user from one tenant cannot use a refresh token belonging to another tenant.
- [ ] Refresh‑token replay attacks are rejected as per the single‑use rule.

## Open Questions
- None (all major decisions finalized).
