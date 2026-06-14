'''Tenant‑scoped query helper.

This utility constructs a SQLAlchemy ``select()`` that automatically filters
by the current ``tenant_id``.  It supports two patterns that appear in the
data model:

1. **Direct ``tenant_id`` column** – e.g. the ``Organization`` model defines a
   ``tenant_id`` foreign‑key column.  In that case we simply add a ``WHERE``
   clause on the column.
2. **Indirect via ``org_id``** – the ``User`` model does not contain a
   ``tenant_id`` column; it references an ``Organization`` via ``org_id``.  We
   join the ``Organization`` table and filter on ``Organization.tenant_id``.

If the model has neither a ``tenant_id`` nor an ``org_id`` column we raise a
``ValueError`` so that missing tenant isolation is detected loudly during
development.
'''

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# The ``Organization`` model is defined in ``packages.database.models.organization``.
# Import is placed inside the function to avoid circular‑import issues when this
# module is imported by repository implementations that also import the models.


async def tenant_scoped_query(
    session: AsyncSession,
    model: Any,
    tenant_id: Any,
    **filters: Any,
) -> Any:
    """Return a ``select`` statement scoped to ``tenant_id``.

    Args:
        session: The async SQLAlchemy session (currently unused but kept for a
            future‑proof signature that matches repository helpers).
        model: The SQLAlchemy ORM model class to query.
        tenant_id: The UUID (or compatible type) of the tenant to restrict the
            query to.
        **filters: Additional column filters to apply (e.g. ``name="Acme"``).

    Returns:
        A ``select`` object that callers can ``await session.execute(...)``.

    Raises:
        ValueError: If the model does not provide a direct ``tenant_id`` column
            nor an ``org_id`` column that can be joined to ``Organization``.
    """

    # 1️⃣ Direct ``tenant_id`` column?
    if "tenant_id" in getattr(model, "__table__", {}).c:
        stmt = select(model).where(model.tenant_id == tenant_id)
    # 2️⃣ Indirect via ``org_id`` -> join ``Organization``
    elif "org_id" in getattr(model, "__table__", {}).c:
        # Local import to avoid circular dependencies.
        from packages.database.models import Organization

        stmt = (
            select(model)
            .join(Organization, model.org_id == Organization.id)
            .where(Organization.tenant_id == tenant_id)
        )
    else:
        raise ValueError(
            f"Model {model.__name__} has no direct 'tenant_id' column or 'org_id' "
            "column to resolve tenant isolation."
        )

    # Apply any additional column filters supplied by the caller.
    for attr, value in filters.items():
        column = getattr(model, attr, None)
        if column is None:
            raise ValueError(
                f"Filter column '{attr}' not found on model {model.__name__}."
            )
        stmt = stmt.where(column == value)

    return stmt
