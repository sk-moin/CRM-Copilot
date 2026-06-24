#tests/integration/test_contact_api.py
import pytest
import uuid

# CREATE
@pytest.mark.asyncio
async def test_create_contact(authed_client, seeded_company):
    response = await authed_client.post(
        "/contacts/",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "company_id": str(seeded_company.id),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "john@example.com"
    assert data["company_id"] == str(seeded_company.id)

# GET by ID
@pytest.mark.asyncio
async def test_get_contact_by_id(authed_client, seeded_company):
    # First create a contact
    create_resp = await authed_client.post(
        "/contacts/",
        json={
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "company_id": str(seeded_company.id),
        },
    )
    contact_id = create_resp.json()["id"]

    response = await authed_client.get(f"/contacts/{contact_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["email"] == "jane@example.com"

# LIST
@pytest.mark.asyncio
async def test_list_contacts(authed_client):
    response = await authed_client.get("/contacts/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# PATCH
@pytest.mark.asyncio
async def test_update_contact(authed_client, seeded_company):
    create_resp = await authed_client.post(
        "/contacts/",
        json={
            "first_name": "Bob",
            "last_name": "Brown",
            "email": "bob@example.com",
            "company_id": str(seeded_company.id),
        },
    )
    contact_id = create_resp.json()["id"]

    response = await authed_client.patch(
        f"/contacts/{contact_id}",
        json={"email": "bob.updated@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "bob.updated@example.com"

# DELETE
@pytest.mark.asyncio
async def test_delete_contact(authed_client, seeded_company):
    create_resp = await authed_client.post(
        "/contacts/",
        json={
            "first_name": "Del",
            "last_name": "User",
            "email": "del@example.com",
            "company_id": str(seeded_company.id),
        },
    )
    contact_id = create_resp.json()["id"]

    response = await authed_client.delete(f"/contacts/{contact_id}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

# 404
@pytest.mark.asyncio
async def test_get_contact_not_found(authed_client):
    response = await authed_client.get(f"/contacts/{uuid.uuid4()}")
    assert response.status_code == 404