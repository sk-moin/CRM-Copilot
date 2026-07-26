"""Prompt loader service."""

from __future__ import annotations

from uuid import UUID

from app.services.llm.prompt_cache import PromptCache
from packages.database.models.prompt_version import PromptVersion
from packages.database.repositories.prompt_repository import PromptRepository
from packages.database.repositories.prompt_version_repository import (
    PromptVersionRepository,
)


class PromptLoader:
    """
    Loads active prompt versions from storage.

    This class is responsible for retrieving the latest active prompt
    version and optionally caching it for faster access.
    """

    def __init__(
        self,
        prompt_repository: PromptRepository,
        prompt_version_repository: PromptVersionRepository,
        cache: PromptCache | None = None,
    ) -> None:
        self.prompt_repository = prompt_repository
        self.prompt_version_repository = prompt_version_repository
        self.cache = cache

    async def load_prompt(
        self,
        *,
        org_id: UUID,
        name: str,
    ) -> PromptVersion | None:
        """
        Load the latest active prompt version.

        Args:
            org_id:
                Organization ID.

            name:
                Logical prompt name.

        Returns:
            Active PromptVersion or None.
        """

        cache_key = f"{org_id}:{name}"

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        prompt = await self.prompt_repository.get_by_name(
            org_id=org_id,
            name=name,
        )

        if prompt is None:
            return None

        version = await self.prompt_version_repository.get_latest_version(
            prompt.id,
        )

        if version is None:
            return None

        if self.cache:
            await self.cache.set(
                cache_key,
                version,
            )

        return version

    async def invalidate(
        self,
        *,
        org_id: UUID,
        name: str,
    ) -> None:
        """
        Remove a prompt from the cache.
        """

        if self.cache is None:
            return

        await self.cache.delete(
            f"{org_id}:{name}",
        )

    async def clear_cache(self) -> None:
        """
        Clear the entire prompt cache.
        """

        if self.cache is None:
            return

        await self.cache.clear()