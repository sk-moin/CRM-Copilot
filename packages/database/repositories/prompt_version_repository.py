"""Repository for PromptVersion entities."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.prompt_version import PromptVersion
from packages.database.models.prompt import Prompt 
from packages.database.repositories.base_repository import BaseRepository


class PromptVersionRepository(BaseRepository):
    """Repository for PromptVersion-specific database operations."""

    model = PromptVersion

    def __init__(
        self,
        session: AsyncSession,
        tenant_id,
    ):
        super().__init__(session, tenant_id)

    async def list_versions(
        self,
        prompt_id,
    ) -> list[PromptVersion]:
        """
        Return all versions for a prompt ordered newest first.
        """

        stmt = (
            select(PromptVersion)
            .join(PromptVersion.prompt)
            .where(
                PromptVersion.prompt_id == prompt_id,
                Prompt.tenant_id == self.tenant_id,
            )
            .order_by(
                desc(PromptVersion.version),
            )
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_version(
        self,
        prompt_id,
    ) -> PromptVersion | None:
        """
        Return the highest version number for a prompt.
        """

        stmt = (
            select(PromptVersion)
            .join(PromptVersion.prompt)
            .where(
                PromptVersion.prompt_id == prompt_id,
                Prompt.tenant_id == self.tenant_id,
            )
            .order_by(
                desc(PromptVersion.version),
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        version_id,
    ) -> PromptVersion | None:
        """
        Retrieve a prompt version by ID.
        """

        stmt = (
            select(PromptVersion)
            .join(PromptVersion.prompt)
            .where(
                PromptVersion.id == version_id,
                Prompt.tenant_id == self.tenant_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_version(
        self,
        prompt_id,
        version: int,
    ) -> PromptVersion | None:
        """
        Retrieve a specific version of a prompt.
        """

        stmt = (
            select(PromptVersion)
            .join(PromptVersion.prompt)
            .where(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.version == version,
                Prompt.tenant_id == self.tenant_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()