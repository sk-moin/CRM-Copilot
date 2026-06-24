"""Tenant-scoped query helper."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def tenant_scoped_query(
    session: AsyncSession,
    model: Any,
    tenant_id: Any,
    **filters: Any,
) -> Any:
    """Return a select statement scoped to tenant_id."""
    print(model.__name__)
    print(model.__table__.c.keys())

    # Every tenant-scoped model must define tenant_id
    if "tenant_id" not in model.__table__.c:
        raise ValueError(
            f"Model {model.__name__} must define a tenant_id column "
            "to support tenant isolation."
        )

    stmt = select(model).where(model.tenant_id == tenant_id)

    # Apply additional filters
    for attr, value in filters.items():
        column = getattr(model, attr, None)

        if column is None:
            raise ValueError(
                f"Filter column '{attr}' not found on model "
                f"{model.__name__}."
            )

        stmt = stmt.where(column == value)

    return stmt