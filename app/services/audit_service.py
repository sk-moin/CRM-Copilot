"""Audit Service – high-level orchestrator for audit log creation.

This service isolates the CRUD layer and provides convenience helpers for
creating audit events from other services.

Responsibilities:
* Create audit events through AuditRepository.
* Provide convenience wrappers for CREATE/UPDATE/DELETE actions.
* Expose timeline retrieval helpers.
* Build entity snapshots for audit storage.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import date, datetime
from packages.database.models import AuditAction, AuditLog
from packages.database.repositories.audit_repository import AuditRepository


class AuditService:
    """Service responsible for creating and querying audit events."""

    @staticmethod
    def _json_safe(value):
        if isinstance(value, dict):
            return {
                k: AuditService._json_safe(v)
                for k, v in value.items()
            }

        if isinstance(value, list):
            return [
                AuditService._json_safe(v)
                for v in value
            ]

        if isinstance(value, tuple):
            return tuple(
                AuditService._json_safe(v)
                for v in value
            )

        if isinstance(value, uuid.UUID):
            return str(value)

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, (date, datetime)):
            return value.isoformat()

        return value

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        current_user: Optional[Any] = None,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._current_user = current_user

        self._repo = AuditRepository(
            session=session,
            tenant_id=tenant_id,
        )

    # ------------------------------------------------------------------ #
    # Core audit logging
    # ------------------------------------------------------------------ #

    async def log_event(
        self,
        *,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None,
        before_values: Optional[dict] = None,
        after_values: Optional[dict] = None,
        event_metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        actor_type: Optional[str] = None,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> AuditLog:
        """Create a new audit log entry."""

        user_id = None

        if self._current_user is not None:
            user_id = getattr(self._current_user, "id", None)

        if org_id is None and self._current_user is not None:
            org_id = getattr(self._current_user, "org_id", None)


        return await self._repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            org_id=org_id,
            user_id=user_id,
            before_values=self._json_safe(before_values),
            after_values=self._json_safe(after_values),
            event_metadata=self._json_safe(event_metadata),
            ip_address=ip_address,
            user_agent=user_agent,
            actor_type=actor_type,
            correlation_id=correlation_id,
        )

    # ------------------------------------------------------------------ #
    # Convenience wrappers
    # ------------------------------------------------------------------ #

    async def log_create(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        after_values: Optional[dict] = None,
        **kwargs,
    ) -> AuditLog:
        return await self.log_event(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            after_values=after_values,
            **kwargs,
        )

    async def log_update(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        before_values: Optional[dict] = None,
        after_values: Optional[dict] = None,
        **kwargs,
    ) -> AuditLog:
        return await self.log_event(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_values=before_values,
            after_values=after_values,
            **kwargs,
        )

    async def log_delete(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        before_values: Optional[dict] = None,
        **kwargs,
    ) -> AuditLog:
        return await self.log_event(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_values=before_values,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    # Timeline helpers
    # ------------------------------------------------------------------ #

    async def get_timeline(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditLog]:
        """Return audit history for a single entity."""

        return await self._repo.list_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )

    async def get_user_activity(
        self,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditLog]:
        """Return audit activity for a user."""

        return await self._repo.list_for_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

    async def get_correlation_events(
        self,
        *,
        correlation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditLog]:
        """Return all events associated with a correlation id."""

        return await self._repo.list_by_correlation_id(
            correlation_id=correlation_id,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------ #
    # Count helpers
    # ------------------------------------------------------------------ #

    async def count_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> int:
        return await self._repo.count_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )


    async def count_for_user(
        self,
        *,
        user_id: uuid.UUID,
    ) -> int:
        return await self._repo.count_for_user(
            user_id=user_id,
        )


    async def count_for_correlation(
        self,
        *,
        correlation_id: uuid.UUID,
    ) -> int:
        return await self._repo.count_for_correlation(
            correlation_id=correlation_id,
        )

    async def count_timeline(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> int:
        """Return the total number of audit entries for an entity."""

        return await self._repo.count_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

    async def count_user_activity(
        self,
        *,
        user_id: uuid.UUID,
    ) -> int:
        """Return the total number of audit entries for a user."""

        return await self._repo.count_for_user(
            user_id=user_id,
        )

    async def count_correlation_events(
        self,
        *,
        correlation_id: uuid.UUID,
    ) -> int:
        """Return the total number of events for a correlation ID."""

        return await self._repo.count_for_correlation(
            correlation_id=correlation_id,
        )

    # ------------------------------------------------------------------ #
    # Snapshot builders
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_snapshot(obj: Any, fields: list[str]) -> dict:
        """Build a safe snapshot from selected fields."""

        snapshot = {}

        for field in fields:
            value = getattr(obj, field, None)

            if isinstance(value, uuid.UUID):
                value = str(value)

            elif isinstance(value, Decimal):
                value = str(value)

            snapshot[field] = value

        return snapshot

    @classmethod
    def build_company_snapshot(cls, company: Any) -> dict:
        return cls.build_snapshot(
            company,
            [
                "id",
                "name",
                "industry",
                "website",
            ],
        )

    @classmethod
    def build_contact_snapshot(cls, contact: Any) -> dict:
        return cls.build_snapshot(
            contact,
            [
                "id",
                "first_name",
                "last_name",
                "email",
                "company_id",
            ],
        )

    @classmethod
    def build_opportunity_snapshot(cls, opportunity: Any) -> dict:
        return cls.build_snapshot(
            opportunity,
            [
                "id",
                "title",
                "stage",
                "value",
            ],
        )

    @classmethod
    def build_task_snapshot(cls, task: Any) -> dict:
        return cls.build_snapshot(
            task,
            [
                "id",
                "title",
                "status",
                "priority",
            ],
        )