"""
Integration tests for Prompt Management API.

These tests verify the complete Prompt Management flow through the
FastAPI API, service layer, repositories, and database.

Spec 008 – Prompt Management
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------
# List Prompts
# ---------------------------------------------------------------------


async def test_list_prompts(
    authed_client: AsyncClient,
):
    response = await authed_client.get(
        "/api/v1/prompts/",
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------
# Create Prompt
# ---------------------------------------------------------------------


async def test_create_prompt(
    authed_client: AsyncClient,
):
    payload = {
        "name": "crm_chat",
        "category": "system",
        "description": "CRM Assistant",
    }

    response = await authed_client.post(
        "/api/v1/prompts/",
        json=payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == payload["name"]
    assert body["category"] == payload["category"]


# ---------------------------------------------------------------------
# Get Prompt
# ---------------------------------------------------------------------


async def test_get_prompt(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    response = await authed_client.get(
        f"/api/v1/prompts/{prompt['id']}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == prompt["id"]


# ---------------------------------------------------------------------
# Update Prompt
# ---------------------------------------------------------------------


async def test_update_prompt(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    response = await authed_client.patch(
        f"/api/v1/prompts/{prompt['id']}",
        json={
            "description": "Updated prompt",
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated prompt"


# ---------------------------------------------------------------------
# Delete Prompt
# ---------------------------------------------------------------------


async def test_delete_prompt(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "delete_prompt",
            "category": "system",
        },
    )

    prompt = create.json()

    response = await authed_client.delete(
        f"/api/v1/prompts/{prompt['id']}",
    )

    assert response.status_code == 204


# ---------------------------------------------------------------------
# Prompt Versions
# ---------------------------------------------------------------------


async def test_list_prompt_versions(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    response = await authed_client.get(
        f"/api/v1/prompts/{prompt['id']}/versions",
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------
# Create Prompt Version
# ---------------------------------------------------------------------


async def test_create_prompt_version(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    payload = {
        "template": "Hello {{ name }}",
        "variables": [
            "name",
        ],
        "temperature": 0.2,
    }

    response = await authed_client.post(
        f"/api/v1/prompts/{prompt['id']}/versions",
        json=payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["template"] == payload["template"]


# ---------------------------------------------------------------------
# Activate Prompt Version
# ---------------------------------------------------------------------


async def test_activate_prompt_version(
    authed_client: AsyncClient,
):
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    version = await authed_client.post(
        f"/api/v1/prompts/{prompt['id']}/versions",
        json={
            "template": "Version 2",
            "variables": [],
        },
    )

    version_id = version.json()["id"]

    response = await authed_client.post(
        f"/api/v1/prompts/{prompt['id']}/activate/{version_id}",
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------
# Render Prompt
# ---------------------------------------------------------------------


async def test_render_prompt(
    authed_client: AsyncClient,
):
    # Create prompt
    create = await authed_client.post(
        "/api/v1/prompts/",
        json={
            "name": "crm_chat",
            "category": "system",
        },
    )

    prompt = create.json()

    # Create first prompt version
    version = await authed_client.post(
        f"/api/v1/prompts/{prompt['id']}/versions",
        json={
            "template": "Hello {{ name }}",
            "variables": ["name"],
        },
    )

    assert version.status_code == 201

    # Render prompt
    response = await authed_client.post(
        f"/api/v1/prompts/{prompt['id']}/render/",
        json={
            "variables": {
                "name": "Alice",
            },
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["prompt"] == "Hello Alice"


# ---------------------------------------------------------------------
# Not Found
# ---------------------------------------------------------------------


async def test_prompt_not_found(
    authed_client: AsyncClient,
):
    response = await authed_client.get(
        "/api/v1/prompts/00000000-0000-0000-0000-000000000000",
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------
# Unauthorized
# ---------------------------------------------------------------------


async def test_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/prompts/",
    )

    assert response.status_code == 401