# app/api/routes/opportunity.py
"""FastAPI router for Opportunity CRUD operations.

Exception mapping:
* EntityNotFoundError → 404
* BusinessRuleViolationError → 400
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_opportunity_service
from app.api.schemas.opportunity import (
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityResponse,
)
from app.services.opportunity_service import OpportunityService
from app.services.exceptions import EntityNotFoundError, BusinessRuleViolationError

router = APIRouter()

@router.post("/", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    payload: OpportunityCreate,
    service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityResponse:
    try:
        opp = await service.create_opportunity(**payload.model_dump())
        return opp
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def read_opportunity(
    opportunity_id: UUID,
    service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityResponse:
    try:
        return await service.get_opportunity(str(opportunity_id))
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get("/", response_model=List[OpportunityResponse])
async def list_opportunities(
    service: OpportunityService = Depends(get_opportunity_service),
) -> List[OpportunityResponse]:
    return await service.list_opportunities()

@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: UUID,
    payload: OpportunityUpdate,
    service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityResponse:
    try:
        return await service.update_opportunity(
            str(opportunity_id), **payload.model_dump(exclude_unset=True)
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
