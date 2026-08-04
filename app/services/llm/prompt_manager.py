"""
Prompt Manager.

High-level interface for loading and rendering prompts.

Responsibilities
----------------
- Load active prompt templates
- Render prompt templates
- Check prompt existence

The PromptManager intentionally delegates persistence to
PromptLoader and rendering to PromptRenderer.
"""

from __future__ import annotations

from typing import Any

from app.observability.tracing import trace_context, traced
from app.services.llm.prompt_loader import PromptLoader
from app.services.llm.prompt_renderer import PromptRenderer


class PromptManager:
    """
    High-level Prompt Manager.

    This class combines PromptLoader and PromptRenderer into a
    single API that can be consumed by AI services.

    It does not access repositories directly.
    """

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader,
        prompt_renderer: PromptRenderer,
    ) -> None:
        self.prompt_loader = prompt_loader
        self.prompt_renderer = prompt_renderer

    @traced(
        name="prompt-load",
        run_type="chain",
        tags=["prompt"],
    )
    async def get_prompt(
        self,
        *,
        org_id,
        name: str,
    ) -> str | None:
        """
        Return the active prompt template.
        """

        with trace_context(
            metadata={
                "prompt_name": name,
                "organization_id": str(org_id),
            },
            tags=["prompt", "load"],
        ):
            version = await self.prompt_loader.load_prompt(
                org_id=org_id,
                name=name,
            )

        if version is None:
            return None

        return version.template

    @traced(
        name="prompt-render",
        run_type="chain",
        tags=["prompt"],
    )
    async def render_prompt(
        self,
        *,
        org_id,
        name: str,
        variables: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Render a prompt template.
        """

        template = await self.get_prompt(
            org_id=org_id,
            name=name,
        )

        if template is None:
            return None

        with trace_context(
            metadata={
                "prompt_name": name,
                "organization_id": str(org_id),
                "variable_count": len(variables or {}),
            },
            tags=["prompt", "render"],
        ):
            return self.prompt_renderer.render(
                template,
                variables or {},
            )

    async def prompt_exists(
        self,
        *,
        org_id,
        name: str,
    ) -> bool:
        """
        Check whether a prompt exists.
        """

        template = await self.get_prompt(
            org_id=org_id,
            name=name,
        )

        return template is not None

    async def invalidate_cache(
        self,
        *,
        org_id,
        name: str,
    ) -> None:
        """
        Remove a prompt from cache.
        """

        await self.prompt_loader.invalidate(
            org_id=org_id,
            name=name,
        )

    async def clear_cache(
        self,
    ) -> None:
        """
        Clear all cached prompts.
        """

        await self.prompt_loader.clear_cache()