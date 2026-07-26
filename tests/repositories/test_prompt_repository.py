"""
Tests for PromptRepository.
"""

from __future__ import annotations

import uuid

import pytest

from packages.database.models.prompt import (
    Prompt,
    PromptCategory,
)
from packages.database.repositories.prompt_repository import (
    PromptRepository,
)
from packages.database.models.tenant import Tenant


pytestmark = pytest.mark.asyncio


async def test_create_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Repository should create a Prompt.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    prompt = await repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
        description="CRM chat prompt",
    )

    assert prompt.id is not None
    assert prompt.name == "crm_chat"
    assert prompt.category == PromptCategory.SYSTEM
    assert prompt.org_id == organization.id


async def test_get_prompt_by_id(
    async_session,
    tenant,
    organization,
):
    """
    Repository should retrieve a Prompt by id.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    created = await repository.create(
        org_id=organization.id,
        name="retrieval",
        category=PromptCategory.RAG,
    )

    found = await repository.get_by_id(
        created.id,
    )

    assert found is not None
    assert found.id == created.id


async def test_list_prompts(
    async_session,
    tenant,
    organization,
):
    """
    Repository should list tenant prompts.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    await repository.create(
        org_id=organization.id,
        name="prompt_one",
        category=PromptCategory.SYSTEM,
    )

    await repository.create(
        org_id=organization.id,
        name="prompt_two",
        category=PromptCategory.RAG,
    )

    prompts = await repository.list()

    assert len(prompts) >= 2


async def test_update_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Repository should update prompt metadata.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    prompt = await repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    updated = await repository.update(
        prompt.id,
        description="Updated description",
    )

    assert updated is not None
    assert updated.description == "Updated description"


async def test_delete_prompt(
    async_session,
    tenant,
    organization,
):
    """
    Repository should delete prompts.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    prompt = await repository.create(
        org_id=organization.id,
        name="temporary",
        category=PromptCategory.SYSTEM,
    )

    deleted = await repository.delete(
        prompt.id,
    )

    assert deleted is True

    assert (
        await repository.get_by_id(prompt.id)
        is None
    )


async def test_get_unknown_prompt_returns_none(
    async_session,
    tenant,
):
    """
    Unknown ids should return None.
    """

    repository = PromptRepository(
        async_session,
        tenant.id,
    )

    prompt = await repository.get_by_id(
        uuid.uuid4(),
    )

    assert prompt is None


async def test_prompt_is_tenant_scoped(
    async_session,
    tenant,
    organization,
):
    """
    Prompts must not leak across tenants.
    """

    another_tenant = Tenant(
        name="Tenant Two",
        subdomain="tenant-two",
    )

    async_session.add(another_tenant)
    await async_session.flush()
    await async_session.refresh(another_tenant)

    repo_one = PromptRepository(
        async_session,
        tenant.id,
    )

    repo_two = PromptRepository(
        async_session,
        another_tenant.id,
    )

    prompt = await repo_one.create(
        org_id=organization.id,
        name="private_prompt",
        category=PromptCategory.SYSTEM,
    )

    assert (
        await repo_two.get_by_id(prompt.id)
        is None
    )