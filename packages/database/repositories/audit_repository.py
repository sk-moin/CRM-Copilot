"""Audit Repository – tenant-scoped, immutable audit log queries."""

from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import AuditLog
from packages.database.repositories import BaseRepository


class AuditRepository(BaseRepository):
    """Repository that handles immutable audit log queries."""

    model = AuditLog

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        super().__init__(
            session=session,
            tenant_id=tenant_id,
        )

    async def create(
        self,
        **kwargs,
    ) -> AuditLog:
        """Create a new immutable audit log."""

        required_fields = {
            "action",
            "entity_type",
            "entity_id",
        }

        missing = required_fields - kwargs.keys()

        if missing:
            raise ValueError(
                f"Missing required audit fields: {', '.join(sorted(missing))}"
            )

        audit = AuditLog(
            tenant_id=self.tenant_id,
            **kwargs,
        )

        self.session.add(audit)
        await self.session.flush()

        return audit

    async def list_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AuditLog]:
        offset = (page - 1) * page_size

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(page_size)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AuditLog]:
        offset = (page - 1) * page_size

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.user_id == user_id,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(page_size)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_tenant(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AuditLog]:
        offset = (page - 1) * page_size

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(page_size)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_correlation_id(
        self,
        *,
        correlation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AuditLog]:
        offset = (page - 1) * page_size

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.correlation_id == correlation_id,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(page_size)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
        )

        rows = await self.session.execute(select(AuditLog))
        print("VISIBLE ROWS:", rows.scalars().all())

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_for_user(
        self,
        *,
        user_id: uuid.UUID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.user_id == user_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_for_correlation(
        self,
        *,
        correlation_id: uuid.UUID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.correlation_id == correlation_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, *_, **__):
        raise NotImplementedError("Audit logs are immutable; update is not allowed.")

    async def delete(self, *_, **__):
        raise NotImplementedError("Audit logs are immutable; delete is not allowed.")
