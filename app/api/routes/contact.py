# app/api/routes/contact.py
"""FastAPI router for Contact CRUD operations.

Maps service exceptions to HTTP status codes:
* ``EntityNotFoundError`` → 404
* ``BusinessRuleViolationError`` → 400
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_contact_service
from app.api.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.services.contact_service import ContactService
from app.services.exceptions import EntityNotFoundError, BusinessRuleViolationError

router = APIRouter()

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    service: ContactService = Depends(get_contact_service),
) -> ContactResponse:
    try:
        contact = await service.create_contact(**payload.model_dump())
        return contact
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: UUID,
    service: ContactService = Depends(get_contact_service),
) -> ContactResponse:
    try:
        return await service.get_contact(str(contact_id))
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get("/", response_model=List[ContactResponse])
async def list_contacts(
    service: ContactService = Depends(get_contact_service),
) -> List[ContactResponse]:
    return await service.list_contacts()

@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    service: ContactService = Depends(get_contact_service),
) -> ContactResponse:
    try:
        return await service.update_contact(
            str(contact_id), **payload.model_dump(exclude_unset=True)
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: UUID,
    service: ContactService = Depends(get_contact_service),
) -> dict:
    try:
        await service.delete_contact(str(contact_id))
        return {"deleted": True}
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
