import pytest
import uuid


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _create_opportunity(
    authed_client,
    seeded_company,
    seeded_user,
):
    response = await authed_client.post(
        "/opportunities/",
        json={
            "title": "Test Opportunity",
            "stage": "LEAD",
            "company_id": str(seeded_company.id),
            "owner_user_id": str(seeded_user.id),
            "probability": 25,
            "value": "1000.00",
        },
    )

    assert response.status_code == 201

    return response.json()


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_opportunity(
    authed_client,
    seeded_company,
    seeded_user,
):
    response = await authed_client.post(
        "/opportunities/",
        json={
            "title": "Enterprise CRM Deal",
            "stage": "LEAD",
            "company_id": str(seeded_company.id),
            "owner_user_id": str(seeded_user.id),
            "probability": 25,
            "value": "50000.00",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["title"] == "Enterprise CRM Deal"
    assert data["stage"] == "LEAD"
    assert data["company_id"] == str(seeded_company.id)
    assert data["owner_user_id"] == str(seeded_user.id)
    assert data["probability"] == 25


# ------------------------------------------------------------------
# GET BY ID
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_opportunity_by_id(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.get(
        f"/opportunities/{opportunity['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == opportunity["id"]
    assert data["title"] == "Test Opportunity"
    assert data["stage"] == "LEAD"


# ------------------------------------------------------------------
# LIST
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_opportunities(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.get("/opportunities/")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert any(
        item["id"] == opportunity["id"]
        for item in data
    )


# ------------------------------------------------------------------
# PATCH
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_opportunity(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.patch(
        f"/opportunities/{opportunity['id']}",
        json={
            "stage": "PROPOSAL",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["stage"] == "PROPOSAL"


# ------------------------------------------------------------------
# VALIDATION ERRORS
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_opportunity_invalid_stage(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.patch(
        f"/opportunities/{opportunity['id']}",
        json={
            "stage": "INVALID_STAGE",
        },
    )

    # Literal validation in schema
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_patch_opportunity_negative_value(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.patch(
        f"/opportunities/{opportunity['id']}",
        json={
            "value": -100,
        },
    )

    assert response.status_code == 400

    assert "negative" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_opportunity_invalid_probability(
    authed_client,
    seeded_company,
    seeded_user,
):
    opportunity = await _create_opportunity(
        authed_client,
        seeded_company,
        seeded_user,
    )

    response = await authed_client.patch(
        f"/opportunities/{opportunity['id']}",
        json={
            "probability": 150,
        },
    )

    # Pydantic schema enforces <=100
    assert response.status_code in (400, 422)


# ------------------------------------------------------------------
# NOT FOUND
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_opportunity_not_found(
    authed_client,
):
    response = await authed_client.get(
        f"/opportunities/{uuid.uuid4()}"
    )

    assert response.status_code == 404

    assert "not found" in response.json()["detail"].lower()