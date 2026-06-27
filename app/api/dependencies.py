# app/api/dependencies.py
"""FastAPI dependency injection utilities.

Provides:
* ``get_current_user`` – validates a JWT (via ``app.core.security``), loads the
  corresponding ``User`` ORM object, and returns it for downstream services.
* Service factories – one per core CRUD service, each receiving a DB session
  and the authenticated ``User``.

All imports are limited to the core utilities, repository layer, and service
layer. No router code, no FastAPI app creation, and no side‑effects at import
time.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_jwt, JWTError

from packages.database.models import User
from packages.database.repositories.user_repository import UserRepository

from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.opportunity_service import OpportunityService
from app.services.task_service import TaskService
from app.services.audit_service import AuditService

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> User:
    """FastAPI dependency that returns the authenticated ``User``.

    Steps:
    1. Extract the raw JWT from the ``Authorization: Bearer <token>`` header.
    2. Decode & verify it with ``decode_jwt`` – ``JWTError`` translates to a 401.
    3. Pull ``sub`` (user id) and ``tenant_id`` from the payload.
    4. Load the ``User`` ORM object via ``UserRepository`` scoped to the tenant.
    5. If the user is missing or the token is malformed, raise ``401``.
    """
    try:
        payload = decode_jwt(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    repo = UserRepository(db, tenant_id)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_company_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyService:
    """Factory that provides a ``CompanyService`` instance for the request."""
    return CompanyService(session=db, current_user=current_user)


def get_contact_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactService:
    """Factory that provides a ``ContactService`` instance for the request."""
    return ContactService(session=db, current_user=current_user)


def get_opportunity_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityService:
    """Factory that provides an ``OpportunityService`` instance for the request."""
    return OpportunityService(session=db, current_user=current_user)


def get_task_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskService:
    """Factory that provides a ``TaskService`` instance for the request."""
    return TaskService(session=db, current_user=current_user)


def get_audit_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditService:
    return AuditService(
        session=db,
        tenant_id=current_user.tenant_id,
        current_user=current_user,
    )

__all__ = [
    "get_current_user",
    "get_company_service",
    "get_contact_service",
    "get_opportunity_service",
    "get_task_service",
    "get_audit_service",
]
