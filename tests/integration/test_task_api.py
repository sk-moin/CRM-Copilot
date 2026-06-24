import pytest
import uuid

# ---------------------------------------------------
# Task integration tests – full coverage
# ---------------------------------------------------

@pytest.mark.asyncio
async def test_create_task(authed_client, seeded_user):
    """Baseline create test (already existed)."""
    resp = await authed_client.post(
        "/tasks/",
        json={
            "title": "Follow up with customer",
            "description": "Schedule product demo",
            "status": "PENDING",
            "priority": "HIGH",
            "assigned_to_user_id": str(seeded_user.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["title"] == "Follow up with customer"
    assert data["description"] == "Schedule product demo"
    assert data["status"] == "PENDING"
    assert data["priority"] == "HIGH"
    assert data["assigned_to_user_id"] == str(seeded_user.id)

# Helper to create a task for other tests
async def _create_task(authed_client, seeded_user):
    resp = await authed_client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A task for testing",
            "status": "PENDING",
            "priority": "MEDIUM",
            "assigned_to_user_id": str(seeded_user.id),
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]

@pytest.mark.asyncio
async def test_get_task_by_id(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    resp = await authed_client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task_id
    assert data["title"] == "Test Task"

@pytest.mark.asyncio
async def test_list_tasks(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    resp = await authed_client.get("/tasks/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [item["id"] for item in data]
    assert task_id in ids

@pytest.mark.asyncio
async def test_patch_task(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    resp = await authed_client.patch(
        f"/tasks/{task_id}",
        json={"status": "COMPLETED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"

@pytest.mark.asyncio
async def test_patch_task_invalid_assignee(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    random_user = str(uuid.uuid4())
    resp = await authed_client.patch(
        f"/tasks/{task_id}",
        json={"assigned_to_user_id": random_user},
    )
    # Service raises EntityNotFoundError → 404
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_patch_task_invalid_entity_pair_missing_type(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    # Provide entity_id only
    resp = await authed_client.patch(
        f"/tasks/{task_id}",
        json={"entity_id": str(uuid.uuid4())},
    )
    # Could be 400 (service) or 422 (schema) – we accept either
    assert resp.status_code in (400, 422)

@pytest.mark.asyncio
async def test_patch_task_invalid_entity_pair_missing_id(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    # Provide entity_type only
    resp = await authed_client.patch(
        f"/tasks/{task_id}",
        json={"entity_type": "company"},
    )
    assert resp.status_code in (400, 422)

@pytest.mark.asyncio
async def test_patch_task_invalid_entity_type(authed_client, seeded_user):
    task_id = await _create_task(authed_client, seeded_user)
    resp = await authed_client.patch(
        f"/tasks/{task_id}",
        json={"entity_type": "invalid", "entity_id": str(uuid.uuid4())},
    )
    # Service raises BusinessRuleViolationError → 400 (or 422 if schema catches)
    assert resp.status_code in (400, 422)

@pytest.mark.asyncio
async def test_get_task_not_found(authed_client):
    random_id = str(uuid.uuid4())
    resp = await authed_client.get(f"/tasks/{random_id}")
    assert resp.status_code == 404
