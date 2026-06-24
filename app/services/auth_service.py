"""Authentication service implementation for Spec 001.

This service provides the core business‑logic functions required by the spec:
* ``register`` – create tenant, default organization, and owner user in a
  single transaction.
* ``login`` – verify credentials and issue an access token plus a refresh
  token.
* ``refresh`` – rotate the refresh token, ensuring single‑use semantics.
* ``get_profile`` – decode the access token and return the user profile payload.

The implementation deliberately avoids any FastAPI router or Pydantic schema –
only pure Python functions and the repository layer are used, as required by the
task.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Dict

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    parse_refresh_token,
    verify_password,
    decode_jwt,
)
from app.core.redis_client import get_redis, token_hash
from app.services.exceptions import (
    DuplicateEmailError,
    DuplicateSubdomainError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from packages.database.models import Tenant, Organization, User
from packages.database.repositories.base_repository import BaseRepository
from packages.database.repositories.tenant_repository import TenantRepository
from packages.database.repositories.organization_repository import OrganizationRepository
from packages.database.repositories.user_repository import UserRepository
from app.core import config

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

async def _email_exists(session, email: str) -> bool:
    """Return ``True`` if a user with ``email`` exists in the system.

    The ``User`` model has a globally unique ``email`` column, so we can query
    without tenant scoping.
    """
    stmt = User.__table__.select().where(User.email == email)
    result = await session.execute(stmt)
    return result.first() is not None

async def _org_subdomain_exists(session, subdomain: str) -> bool:
    """Check whether an organization with the given subdomain already exists."""
    stmt = Organization.__table__.select().where(Organization.subdomain == subdomain)
    result = await session.execute(stmt)
    return result.first() is not None

# ---------------------------------------------------------------------------
# Public service API
# ---------------------------------------------------------------------------

class AuthService:
    """Business‑logic layer for authentication and RBAC.

    All methods are ``async`` and expect an ``AsyncSession`` that the caller
    provides (the test suite supplies the fixture ``async_session``).
    """

    def __init__(self, session):
        self.session = session
        self.redis = get_redis()

    # ---------------------------------------------------------------
    # Register
    # ---------------------------------------------------------------
    async def register(
        self,
        email: str,
        password: str,
        subdomain: str,
        org_name: str,
    ) -> Dict[str, str]:
        """Create a tenant, default organization, and owner user.

        The operation runs inside a single transaction; any failure rolls back
        the whole process.  The function returns a dict containing the newly
        created ``access_token`` and ``refresh_token``.
        """
        # 1️⃣ Validate uniqueness constraints before starting the transaction.
        if await _email_exists(self.session, email):
            raise DuplicateEmailError()
        if await _org_subdomain_exists(self.session, subdomain):
            raise DuplicateSubdomainError()

        
        # Create Tenant directly (no repository needed)
        tenant = Tenant(name=subdomain, subdomain=subdomain)
        self.session.add(tenant)
        await self.session.flush()  # assign PK

        # Create Organization tied to the tenant
        organization = Organization(
            name=org_name, subdomain=subdomain, tenant_id=tenant.id
        )
        self.session.add(organization)
        await self.session.flush()

        # Create Owner User
        user = User(
            email=email,
            password_hash=hash_password(password),
            role="OWNER",
            org_id=organization.id,
            tenant_id=organization.tenant_id,
        )
        self.session.add(user)
        await self.session.flush()

        await self.session.commit()

            # Generate tokens (no commit yet – the surrounding ``begin`` will commit)
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            org_id=organization.id,
            email=email,
            role="OWNER",
        )
        refresh_token = create_refresh_token()
        # Store hashed refresh token in Redis with the configured TTL
        await self.redis.set(
            f"refresh:{token_hash(refresh_token)}",
            json.dumps(
                {
                    "user_id": str(user.id),
                    "tenant_id": str(tenant.id),
                    "org_id": str(organization.id),
                    "role": "OWNER",
                }
            ),
            ex=config.REFRESH_TOKEN_TTL_SECONDS,
        )

        return {"access_token": access_token, "refresh_token": refresh_token}

    # ---------------------------------------------------------------
    # Login
    # ---------------------------------------------------------------
    async def login(self, email: str, password: str) -> Dict[str, str]:
        """Validate credentials and return new access/refresh tokens."""
        from sqlalchemy import select

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        tenant_id = user.organization.tenant_id

        access_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant_id,
            org_id=user.org_id,
            email=user.email,
            role=user.role,
        )

        refresh_token = create_refresh_token()

        await self.redis.set(
            f"refresh:{token_hash(refresh_token)}",
            json.dumps(
                {
                    "user_id": str(user.id),
                    "tenant_id": str(tenant_id),
                    "org_id": str(user.org_id),
                    "role": user.role,
                }
            ),
            ex=config.REFRESH_TOKEN_TTL_SECONDS,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }



    # ---------------------------------------------------------------
    # Refresh
    # ---------------------------------------------------------------
    async def refresh(self, token: str) -> Dict[str, str]:
        """Rotate a refresh token.

        The presented token is hashed and looked up in Redis.  If it does not
        exist (missing or already used) a ``InvalidCredentialsError`` is raised.
        On success the old key is deleted and a new refresh token is stored.
        """
        token_key = f"refresh:{token_hash(token)}"
        stored = await self.redis.get(token_key)
        if stored is None:
            raise InvalidCredentialsError()
        payload = json.loads(stored)
        # Delete old token (single‑use guarantee)
        await self.redis.delete(token_key)
        # Issue new tokens
        access_token = create_access_token(
            user_id=uuid.UUID(payload["user_id"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            org_id=uuid.UUID(payload["org_id"]),
            email="",  # email not needed for new access token generation here
            role=payload["role"],
        )
        new_refresh = create_refresh_token()
        await self.redis.set(
            f"refresh:{token_hash(new_refresh)}",
            json.dumps(payload),
            ex=config.REFRESH_TOKEN_TTL_SECONDS,
        )
        return {"access_token": access_token, "refresh_token": new_refresh}

    # ---------------------------------------------------------------
    # Get profile
    # ---------------------------------------------------------------
    async def get_profile(self, access_token: str) -> Dict[str, str]:
        """Return the profile payload for the authenticated user."""
        payload = decode_jwt(access_token)


        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])

        user_repo = UserRepository(
            self.session,
            tenant_id=tenant_id,
        )

        user = await user_repo.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError()

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "org_id": str(user.org_id),
            "tenant_id": str(user.organization.tenant_id),
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else ""
            ),
        }

# Export a convenient instance creator for callers that already have a session.
def get_auth_service(session) -> AuthService:
    return AuthService(session)
