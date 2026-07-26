"""
Tests for PromptManager.
"""

from __future__ import annotations

import pytest

from packages.database.models.prompt import PromptCategory
from packages.database.repositories.prompt_repository import (
    PromptRepository,
)
from packages.database.repositories.prompt_version_repository import (
    PromptVersionRepository,
)
from app.services.llm.prompt_loader import PromptLoader
from app.services.llm.prompt_renderer import PromptRenderer

from app.services.llm.prompt_manager import PromptManager

pytestmark = pytest.mark.asyncio


async def create_prompt(
    session,
    tenant,
    organization,
):
    """
    Helper to create a prompt and its first version.
    """

    prompt_repo = PromptRepository(
        session,
        tenant.id,
    )

    version_repo = PromptVersionRepository(
        session,
        tenant.id,
    )

    prompt = await prompt_repo.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repo.create(
        prompt_id=prompt.id,
        version=1,
        template="Hello {{ name }}",
        variables=["name"],
    )

    prompt.active_version_id = version.id

    await session.flush()
    await session.refresh(prompt)

    return (
        prompt_repo,
        version_repo,
        prompt,
        version,
    )


async def test_get_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Manager should return the active prompt template.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
    )

    renderer = PromptRenderer()

    manager = PromptManager(
        prompt_loader=loader,
        prompt_renderer=renderer,
    )

    template = await manager.get_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    assert template == "Hello {{ name }}"


async def test_render_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Manager should render variables.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
    )

    renderer = PromptRenderer()

    manager = PromptManager(
        prompt_loader=loader,
        prompt_renderer=renderer,
    )

    rendered = await manager.render_prompt(
        org_id=organization.id,
        name="crm_chat",
        variables={
            "name": "Alice",
        },
    )

    assert rendered == "Hello Alice"


async def test_missing_prompt_returns_none(
    async_session,
    tenant,
    organization,
):
    """
    Unknown prompts should return None.
    """

    prompt_repo = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repo = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    manager = PromptManager(
        prompt_loader=PromptLoader(
            prompt_repository=prompt_repo,
            prompt_version_repository=version_repo,
        ),
        prompt_renderer=PromptRenderer(),
    )

    prompt = await manager.get_prompt(
        org_id=organization.id,
        name="does_not_exist",
    )

    assert prompt is None


async def test_render_unknown_prompt_returns_none(
    async_session,
    tenant,
    organization,
):
    """
    Rendering an unknown prompt should return None.
    """

    prompt_repo = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repo = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    manager = PromptManager(
        prompt_loader=PromptLoader(
            prompt_repository=prompt_repo,
            prompt_version_repository=version_repo,
        ),
        prompt_renderer=PromptRenderer(),
    )

    rendered = await manager.render_prompt(
        org_id=organization.id,
        name="missing",
        variables={},
    )

    assert rendered is None


async def test_latest_version_is_used(
    async_session,
    tenant,
    organization,
):
    """
    Active version should always be rendered.
    """

    prompt_repo = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repo = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repo.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    await version_repo.create(
        prompt_id=prompt.id,
        version=1,
        template="Version One",
        variables=[],
    )

    latest = await version_repo.create(
        prompt_id=prompt.id,
        version=2,
        template="Version Two",
        variables=[],
    )

    prompt.active_version_id = latest.id

    await async_session.flush()
    await async_session.refresh(prompt)

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
    )

    renderer = PromptRenderer()

    manager = PromptManager(
        prompt_loader=loader,
        prompt_renderer=renderer,
    )

    rendered = await manager.render_prompt(
        org_id=organization.id,
        name="crm_chat",
        variables={},
    )

    assert rendered == "Version Two"


async def test_missing_variable_kept_by_jinja(
    async_session,
    tenant,
    organization,
):
    """
    Missing variables should not crash rendering.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
    )

    renderer = PromptRenderer()

    manager = PromptManager(
        prompt_loader=loader,
        prompt_renderer=renderer,
    )

    rendered = await manager.render_prompt(
        org_id=organization.id,
        name="crm_chat",
        variables={},
    )

    assert rendered == "Hello "


async def test_render_multiple_variables(
    async_session,
    tenant,
    organization,
):
    """
    Multiple variables should render correctly.
    """

    prompt_repo = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repo = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repo.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repo.create(
        prompt_id=prompt.id,
        version=1,
        template="{{ greeting }} {{ name }}",
        variables=[
            "greeting",
            "name",
        ],
    )

    prompt.active_version_id = version.id

    await async_session.flush()
    await async_session.refresh(prompt)

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
    )

    renderer = PromptRenderer()

    manager = PromptManager(
        prompt_loader=loader,
        prompt_renderer=renderer,
    )

    rendered = await manager.render_prompt(
        org_id=organization.id,
        name="crm_chat",
        variables={
            "greeting": "Hello",
            "name": "Bob",
        },
    )

    assert rendered == "Hello Bob"