#tests/integration/test_company_api.py
import pytest
import pytest_asyncio
from fastapi import status
from packages.database.models.company import Company
from packages.database.repositories.company_repository import CompanyRepository

@pytest.mark.asyncio
async def test_create_company(authed_client):
    response = await authed_client.post(
        "/companies/",
        json={
            "name": "Acme Corp",
            "industry": "Technology",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["name"] == "Acme Corp"
    assert data["industry"] == "Technology"

@pytest.mark.asyncio
async def test_get_company_by_id(authed_client, seeded_company):
    response = await authed_client.get(f"/companies/{seeded_company.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(seeded_company.id)
    assert data["name"] == "Test Company"
    assert data["industry"] == "Technology"

@pytest.mark.asyncio
async def test_list_companies(authed_client, seeded_company):
    response = await authed_client.get("/companies/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "Test Company"

@pytest.mark.asyncio
async def test_patch_company(authed_client, seeded_company):
    response = await authed_client.patch(
        f"/companies/{seeded_company.id}",
        json={"industry": "Software"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["industry"] == "Software"

@pytest.mark.asyncio
async def test_delete_company(authed_client, seeded_company):
    response = await authed_client.delete(f"/companies/{seeded_company.id}")
    assert response.status_code == 200

    assert response.json() == {"deleted": True}

@pytest.mark.asyncio
async def test_get_company_not_found(authed_client):
    import uuid

    non_existent_id = str(uuid.uuid4())
    response = await authed_client.get(f"/companies/{non_existent_id}")
    assert response.status_code == 404

    data = response.json()
    assert "not found" in data["detail"]