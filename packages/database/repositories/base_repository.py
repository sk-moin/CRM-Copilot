"""Base repository implementing tenant‑scoped CRUD operations.

All repository classes in the project inherit from this generic helper. It
accepts an ``AsyncSession`` and the current ``tenant_id`` at construction time
and uses the ``tenant_scoped_query`` utility to guarantee that every query is
restricted to that tenant.

* ``get_by_id`` – Returns the model instance or ``None`` if the row does not
  exist **or** belongs to a different tenant.
* ``list`` – Returns a list of instances matching optional column filters,
  scoped to the tenant.
* ``create`` – Instantiates the model, adds it to the session, and returns the
  new instance (the caller can ``await session.commit()`` later).
* ``update`` – Retrieves the row via ``get_by_id``; if not found returns
  ``None``. Otherwise applies supplied fields and returns the updated instance.
* ``delete`` – Retrieves via ``get_by_id``; if not found returns ``False``.
  On success the instance is removed from the session and ``True`` is returned.

The repository does **not** raise ``NotFoundError`` for missing or out‑of‑
tenant rows, matching the spec’s guidance that “not found” is a normal return
value for the API layer to translate into a 404.
"""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.exceptions import InvalidTenantIdError
from packages.database.queries.tenant_scoped import tenant_scoped_query


class BaseRepository:
    """Generic async repository with tenant isolation."""

    model: Any

    def __init__(self, session: AsyncSession, tenant_id: Any):
        if tenant_id is None:
            raise InvalidTenantIdError(
                "Tenant ID must not be None for tenant-scoped repositories"
            )

        self.session = session
        self.tenant_id = tenant_id

    async def get_by_id(self, id: Any) -> Optional[Any]:
        stmt = await tenant_scoped_query(
            self.session,
            self.model,
            self.tenant_id,
            id=id,
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters: Any) -> List[Any]:
        stmt = await tenant_scoped_query(
            self.session,
            self.model,
            self.tenant_id,
            **filters,
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **data: Any) -> Any:
        # Enforce tenant ownership.
        if hasattr(self.model, "tenant_id"):
            data["tenant_id"] = self.tenant_id

        instance = self.model(**data)

        self.session.add(instance)
        await self.session.flush()

        return instance

    async def update(
        self,
        id: Any,
        **data: Any,
    ) -> Optional[Any]:
        instance = await self.get_by_id(id)

        if instance is None:
            return None

        # Prevent tenant reassignment.
        data.pop("tenant_id", None)

        for attr, value in data.items():
            setattr(instance, attr, value)

        await self.session.flush()
        await self.session.refresh(instance)

        return instance

    async def delete(self, id: Any) -> bool:
        instance = await self.get_by_id(id)

        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()

        return True