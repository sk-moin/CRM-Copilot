"""
Tests for PromptVersionRepository.
"""

from __future__ import annotations

import uuid

import pytest

from packages.database.models.prompt import PromptCategory
from packages.database.repositories.prompt_repository import (
    PromptRepository,
)
from packages.database.repositories.prompt_version_repository import (
    PromptVersionRepository,
)
from sqlalchemy import select
from packages.database.models.prompt import Prompt
from packages.database.models.prompt_version import PromptVersion
from packages.database.models.tenant import Tenant
pytestmark = pytest.mark.asyncio


async def test_create_prompt_version(
    async_session,
    tenant,
    organization,
):
    """
    Repository should create a PromptVersion.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Hello {{ user }}",
        variables=["user"],
    )

    assert version.id is not None
    assert version.prompt_id == prompt.id
    assert version.version == 1
    assert version.template == "Hello {{ user }}"


async def test_get_latest_version(
    async_session,
    tenant,
    organization,
):
    """
    Latest version should be returned.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Version 1",
        variables=[],
    )

    await version_repository.create(
        prompt_id=prompt.id,
        version=2,
        template="Version 2",
        variables=[],
    )

    latest = await version_repository.get_latest_version(
        prompt.id,
    )

    assert latest is not None
    assert latest.version == 2
    assert latest.template == "Version 2"


async def test_list_versions(
    async_session,
    tenant,
    organization,
):
    """
    Repository should return all prompt versions.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="v1",
        variables=[],
    )

    await version_repository.create(
        prompt_id=prompt.id,
        version=2,
        template="v2",
        variables=[],
    )

    versions = await version_repository.list_versions(
        prompt.id,
    )

    assert len(versions) == 2
    assert versions[0].version == 2
    assert versions[1].version == 1


async def test_get_version_by_id(
    async_session,
    tenant,
    organization,
):
    """
    Repository should retrieve a version by id.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Test",
        variables=[],
    )

    found = await version_repository.get_by_id(
        version.id,
    )

    assert found is not None
    assert found.id == version.id


async def test_update_prompt_version(
    async_session,
    tenant,
    organization,
):
    """
    Repository should update PromptVersion metadata.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Old",
        variables=[],
    )

    updated = await version_repository.update(
        version.id,
        template="New",
    )

    assert updated is not None
    assert updated.template == "New"


async def test_delete_prompt_version(
    async_session,
    tenant,
    organization,
):
    """
    Repository should delete PromptVersions.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="crm_chat",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Delete me",
        variables=[],
    )

    deleted = await version_repository.delete(
        version.id,
    )

    assert deleted is True

    assert (
        await version_repository.get_by_id(version.id)
        is None
    )


async def test_get_unknown_version_returns_none(
    async_session,
    tenant,
):
    """
    Unknown ids should return None.
    """

    repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    version = await repository.get_by_id(
        uuid.uuid4(),
    )

    assert version is None


async def test_prompt_version_is_tenant_scoped(
    async_session,
    tenant,
    organization,
):
    """
    Prompt versions must be tenant isolated.
    """

    prompt_repository = PromptRepository(
        async_session,
        tenant.id,
    )

    version_repository = PromptVersionRepository(
        async_session,
        tenant.id,
    )

    another_tenant = Tenant(
        name="Tenant Two",
        subdomain="tenant-two",
    )

    async_session.add(another_tenant)
    await async_session.flush()

    other_repository = PromptVersionRepository(
        async_session,
        another_tenant.id,
    )

    prompt = await prompt_repository.create(
        org_id=organization.id,
        name="private_prompt",
        category=PromptCategory.SYSTEM,
    )

    version = await version_repository.create(
        prompt_id=prompt.id,
        version=1,
        template="Private",
        variables=[],
    )

    assert (
        await other_repository.get_by_id(version.id)
        is None
    )

