"""
PromptService

Business logic for Prompt Management.

Responsibilities
----------------
- Prompt CRUD
- Prompt Version Management
- Prompt Rendering
- Prompt Validation
- Cache invalidation

Routers should interact with this service rather than repositories
directly.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from packages.database.models.prompt import Prompt
from packages.database.models.prompt_version import PromptVersion

from packages.database.repositories.prompt_repository import (
    PromptRepository,
)
from packages.database.repositories.prompt_version_repository import (
    PromptVersionRepository,
)

from app.services.llm.prompt_loader import PromptLoader
from app.services.llm.prompt_manager import PromptManager
from app.services.llm.prompt_renderer import (
    PromptRenderer,
    PromptRenderError,
)
from packages.database.models.user import User

class PromptService:
    """
    High-level Prompt Management service.
    """

    def __init__(
        self,
        *,
        current_user: User,
        prompt_repository: PromptRepository,
        prompt_version_repository: PromptVersionRepository,
        prompt_loader: PromptLoader,
        prompt_renderer: PromptRenderer,
        prompt_manager: PromptManager,
    ) -> None:
        self.current_user = current_user
        self.prompt_repository = prompt_repository
        self.prompt_version_repository = prompt_version_repository
        self.prompt_loader = prompt_loader
        self.prompt_renderer = prompt_renderer
        self.prompt_manager = prompt_manager

    # ------------------------------------------------------------------
    # Prompt CRUD
    # ------------------------------------------------------------------

    async def list_prompts(
        self,
        
    ) -> list[Prompt]:
        """
        Return all prompts belonging to an organization.
        """

        return await self.prompt_repository.list()

    async def create_prompt(
        self,
        **data,
    ) -> Prompt:
        """
        Create a logical prompt.

        Raises:
            HTTPException:
                If a prompt with the same name already exists.
        """

        existing = await self.prompt_repository.get_by_name(
            name=data["name"],
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prompt already exists.",
            )

        return await self.prompt_repository.create(
            **data,
            org_id=self.current_user.org_id,
        )

    async def get_prompt(
        self,
        prompt_id: UUID,
    ) -> Prompt:
        """
        Retrieve a prompt by ID.

        Raises:
            HTTPException:
                If the prompt does not exist.
        """

        prompt = await self.prompt_repository.get_with_versions(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        return prompt

    async def update_prompt(
        self,
        prompt_id: UUID,
        **data,
    ) -> Prompt:
        """
        Update prompt metadata.

        Raises:
            HTTPException:
                If the prompt does not exist.
        """

        prompt = await self.prompt_repository.update(
            prompt_id,
            **data,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        #
        # Metadata changes can affect prompt lookup.
        #
        if "name" in data and data["name"]:
            await self.prompt_loader.invalidate(
                data["name"],
            )

        return prompt

    async def delete_prompt(
        self,
        prompt_id: UUID,
    ) -> None:
        """
        Delete a prompt.

        Raises:
            HTTPException:
                If the prompt does not exist.
        """

        prompt = await self.prompt_repository.get_by_id(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        await self.prompt_repository.delete(
            prompt_id,
        )

        await self.prompt_loader.invalidate(
            org_id=prompt.org_id,
            name=prompt.name,
        )

        # ------------------------------------------------------------------
    # Prompt Versions
    # ------------------------------------------------------------------

    async def list_versions(
        self,
        prompt_id: UUID,
    ) -> list[PromptVersion]:
        """
        Return all versions for a prompt.

        Raises:
            HTTPException:
                If the prompt does not exist.
        """

        prompt = await self.prompt_repository.get_by_id(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        return await self.prompt_version_repository.list_versions(
            prompt_id,
        )

    async def create_version(
        self,
        prompt_id: UUID,
        **data,
    ) -> PromptVersion:
        """
        Create a new immutable prompt version.

        Version numbers are automatically incremented.

        Cache is invalidated after successful creation.

        Raises:
            HTTPException:
                If the prompt does not exist.
        """

        prompt = await self.prompt_repository.get_by_id(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        latest = await self.prompt_version_repository.get_latest_version(
            prompt_id,
        )

        version_number = 1

        if latest is not None:
            version_number = latest.version + 1

        version = await self.prompt_version_repository.create(
            prompt_id=prompt_id,
            version=version_number,
            template=data["template"],
            variables=data.get("variables", []),
            description=data.get("description"),
            llm_model=data.get("model_name"),
            temperature=data.get("temperature", 0.2),
            top_p=data.get("top_p", 1.0),
            max_tokens=data.get("max_tokens"),
            response_format=data.get("response_format"),
            config=data.get("metadata", {}),
        )

        if prompt.active_version_id is None:
            await self.prompt_repository.update(
                prompt_id,
                active_version_id=version.id,
            )

        await self.prompt_loader.invalidate(
            org_id=prompt.org_id,
            name=prompt.name,
        )

        return version

    async def activate_version(
        self,
        prompt_id: UUID,
        version_id: UUID,
    ) -> Prompt:
        """
        Activate a prompt version.

        Raises:
            HTTPException:
                If either the prompt or version cannot be found.
        """

        prompt = await self.prompt_repository.get_by_id(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        version = await self.prompt_version_repository.get_by_id(
            version_id,
        )

        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt version not found.",
            )

        if version.prompt_id != prompt_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Version does not belong to the specified prompt.",
            )

        updated_prompt = await self.prompt_repository.update(
            prompt_id,
            active_version_id=version_id,
        )

        await self.prompt_loader.invalidate(
            org_id=prompt.org_id,
            name=prompt.name,
        )

        return updated_prompt

        # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    async def render_prompt(
        self,
        prompt_id: UUID,
        variables: dict | None = None,
    ) -> str:
        """
        Render the active version of a prompt.

        Raises:
            HTTPException:
                If the prompt or active version does not exist.
        """

        prompt = await self.prompt_repository.get_with_versions(
            prompt_id,
        )

        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        active_version = None

        for version in prompt.versions:
            if version.id == prompt.active_version_id:
                active_version = version
                break

        if active_version is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt has no active version.",
            )

        try:
            return self.prompt_renderer.render(
                template=active_version.template,
                variables=variables or {},
            )

        except PromptRenderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    async def render_system_prompt(
        self,
        *,
        name: str,
        variables: dict | None = None,
    ) -> str:
        """
        Render a prompt by logical name.

        This delegates to PromptManager.
        """

        rendered = await self.prompt_manager.render_prompt(
            name=name,
            variables=variables or {},
        )

        if rendered is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found.",
            )

        return rendered

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_variables(
        self,
        prompt_id: UUID,
        variables: dict | None = None,
    ) -> bool:
        """
        Validate that a prompt can be rendered with the supplied variables.
        """

        prompt = await self.prompt_repository.get_with_versions(
            prompt_id,
        )

        if prompt is None:
            return False

        active_version = None

        for version in prompt.versions:
            if version.id == prompt.active_version_id:
                active_version = version
                break

        if active_version is None:
            return False

        try:
            self.prompt_renderer.validate(
                template=active_version.template,
                variables=variables or {},
            )
            return True

        except PromptRenderError:
            return False

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------

    async def load_prompt(
        self,
        *,
        name: str,
    ) -> PromptVersion | None:
        """
        Load the active prompt version.
        """

        return await self.prompt_loader.load_prompt(
            org_id=self.current_user.org_id,
            name=name,
        )

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    async def invalidate_cache(
        self,
        prompt_name: str,
    ) -> None:
        """
        Remove a prompt from cache.
        """

        await self.prompt_loader.invalidate(
            org_id=self.current_user.org_id,
            name=prompt_name,
        )

    async def clear_cache(
        self,
    ) -> None:
        """
        Clear the entire prompt cache.
        """

        await self.prompt_loader.clear_cache()