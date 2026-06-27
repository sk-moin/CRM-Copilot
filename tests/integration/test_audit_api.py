import uuid

import pytest


@pytest.mark.asyncio
async def test_get_entity_audit(
    authed_client,
    audit_log,
):
    response = await authed_client.get(
        f"/audit/entity/{audit_log.entity_type}/{audit_log.entity_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_type"] == audit_log.entity_type
    assert data["entity_id"] == str(audit_log.entity_id)
    assert data["count"] >= 1
    assert len(data["events"]) >= 1


@pytest.mark.asyncio
async def test_get_user_audit(
    authed_client,
    audit_log,
):
    response = await authed_client.get(
        f"/audit/user/{audit_log.user_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_type"] == "user"
    assert data["entity_id"] == str(audit_log.user_id)
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_get_my_audit(
    authed_client,
):
    response = await authed_client.get("/audit/me")

    assert response.status_code == 200

    data = response.json()

    assert data["entity_type"] == "user"
    assert "events" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_get_correlation_audit(
    authed_client,
    audit_log,
):
    response = await authed_client.get(
        f"/audit/correlation/{audit_log.correlation_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["entity_type"] == "correlation"
    assert data["entity_id"] == str(audit_log.correlation_id)
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_entity_audit_not_found(
    authed_client,
):
    response = await authed_client.get(
        f"/audit/entity/company/{uuid.uuid4()}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 0
    assert data["events"] == []


@pytest.mark.asyncio
async def test_user_audit_not_found(
    authed_client,
):
    response = await authed_client.get(
        f"/audit/user/{uuid.uuid4()}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 0
    assert data["events"] == []


@pytest.mark.asyncio
async def test_correlation_not_found(
    authed_client,
):
    response = await authed_client.get(
        f"/audit/correlation/{uuid.uuid4()}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 0
    assert data["events"] == []