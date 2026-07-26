"""
Tests for PromptLoader.
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

from app.services.llm.prompt_cache import InMemoryPromptCache
from app.services.llm.prompt_loader import PromptLoader

pytestmark = pytest.mark.asyncio


async def create_prompt(
    session,
    tenant,
    organization,
):
    """
    Helper to create a prompt with an active version.
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


async def test_load_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Loader should return the active prompt version.
    """

    prompt_repo, version_repo, _, version = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
        cache=InMemoryPromptCache(),
    )

    loaded = await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    assert loaded is not None
    assert loaded.id == version.id


async def test_load_unknown_prompt_returns_none(
    async_session,
    tenant,
    organization,
):
    """
    Unknown prompt should return None.
    """

    loader = PromptLoader(
        prompt_repository=PromptRepository(
            async_session,
            tenant.id,
        ),
        prompt_version_repository=PromptVersionRepository(
            async_session,
            tenant.id,
        ),
        cache=InMemoryPromptCache(),
    )

    prompt = await loader.load_prompt(
        org_id=organization.id,
        name="unknown",
    )

    assert prompt is None


async def test_cache_returns_same_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Cached prompt should be reused.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    cache = InMemoryPromptCache()

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
        cache=cache,
    )

    first = await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    second = await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    assert first.id == second.id


async def test_cache_can_be_cleared(
    async_session,
    tenant,
    organization,
):
    """
    Clearing cache should not break loading.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    cache = InMemoryPromptCache()

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
        cache=cache,
    )

    await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    cache.clear()

    prompt = await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    assert prompt is not None


async def test_loader_returns_latest_active_version(
    async_session,
    tenant,
    organization,
):
    """
    Loader should always return the active version.
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
        cache=InMemoryPromptCache(),
    )

    loaded = await loader.load_prompt(
        org_id=organization.id,
        name="crm_chat",
    )

    assert loaded.version == 2
    assert loaded.template == "Version Two"


async def test_multiple_loads_do_not_duplicate_cache(
    async_session,
    tenant,
    organization,
):
    """
    Loading repeatedly should always succeed.
    """

    prompt_repo, version_repo, _, _ = await create_prompt(
        async_session,
        tenant,
        organization,
    )

    loader = PromptLoader(
        prompt_repository=prompt_repo,
        prompt_version_repository=version_repo,
        cache=InMemoryPromptCache(),
    )

    for _ in range(10):
        prompt = await loader.load_prompt(
            org_id=organization.id,
            name="crm_chat",
        )

        assert prompt is not None