"""Repository for Prompt entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.database.models.prompt import Prompt
from packages.database.repositories.base_repository import BaseRepository


class PromptRepository(BaseRepository):
    """Repository for Prompt-specific database operations."""

    model = Prompt

    def __init__(self, session: AsyncSession, tenant_id):
        super().__init__(session, tenant_id)

    async def get_by_name(
        self,
        *,
        name: str,
        org_id: str | None = None,
    ) -> Prompt | None:
        """
        Retrieve a prompt by its unique name within an organization.
        """

        stmt = (
            select(Prompt)
            .where(
                Prompt.tenant_id == self.tenant_id,
                Prompt.name == name,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_versions(
        self,
        prompt_id,
    ) -> Prompt | None:
        """
        Retrieve a prompt together with all versions.
        """

        stmt = (
            select(Prompt)
            .options(selectinload(Prompt.versions))
            .where(
                Prompt.tenant_id == self.tenant_id,
                Prompt.id == prompt_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_with_versions(
        self,
        name: str,
    ) -> Prompt | None:
        """
        Retrieve a prompt by name with all versions eagerly loaded.
        """

        stmt = (
            select(Prompt)
            .options(selectinload(Prompt.versions))
            .where(
                Prompt.tenant_id == self.tenant_id,
                Prompt.name == name,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_prompt(
        self,
        name: str,
    ) -> Prompt | None:
        """
        Retrieve a prompt together with its versions.

        The active version is available through
        prompt.active_version_id.
        """

        return await self.get_by_name_with_versions(
            name=name,
        )

    async def list_by_org(
        self,
        org_id,
    ) -> list[Prompt]:
        """
        List all prompts belonging to an organization.
        """

        stmt = (
            select(Prompt)
            .where(
                Prompt.tenant_id == self.tenant_id,
                Prompt.org_id == org_id,
            )
            .order_by(Prompt.name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list(self) -> list[Prompt]:
        """
        List all prompts for the current tenant.
        """

        stmt = (
            select(Prompt)
            .where(
                Prompt.tenant_id == self.tenant_id,
            )
            .order_by(Prompt.name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())