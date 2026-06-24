# app/api/routes/company.py
"""FastAPI router for Company CRUD operations.

All endpoints depend on ``CompanyService`` obtained via the ``get_company_service``
factory in ``app.api.dependencies``.  Service‑layer exceptions are mapped to HTTP
responses:
* ``EntityNotFoundError`` → 404 Not Found
* ``BusinessRuleViolationError`` → 400 Bad Request
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.api.dependencies import get_company_service
from app.api.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)
from app.services.company_service import CompanyService
from app.services.exceptions import EntityNotFoundError, BusinessRuleViolationError

router = APIRouter()

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    try:
        company = await service.create_company(**payload.model_dump())
        return company
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get("/{company_id}", response_model=CompanyResponse)
async def read_company(
    company_id: UUID,
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    try:
        return await service.get_company(str(company_id))
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    service: CompanyService = Depends(get_company_service),
) -> List[CompanyResponse]:
    return await service.list_companies()

@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    service: CompanyService = Depends(get_company_service),
) -> CompanyResponse:
    try:
        return await service.update_company(
            str(company_id), **payload.model_dump(exclude_unset=True)
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    service: CompanyService = Depends(get_company_service),
) -> dict:
    try:
        await service.delete_company(str(company_id))
        return {"deleted": True}
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
