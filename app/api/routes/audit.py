"""FastAPI router for Audit Timeline APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    get_audit_service,
    get_current_user,
)
from app.api.schemas.audit import (
    AuditLogResponse,
    TimelineResponse,
)
from app.services.audit_service import AuditService
from packages.database.models import User
from sqlalchemy import select
from packages.database.models import AuditLog
router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=TimelineResponse,
)
async def get_entity_timeline(
    entity_type: str,
    entity_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_service: AuditService = Depends(get_audit_service),
):
    
    rows = await audit_service._session.execute(select(AuditLog))
    print("API sees:", len(rows.scalars().all()))

    events = await audit_service.get_timeline(
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )

    count = await audit_service.count_for_entity(
        entity_type=entity_type,
        entity_id=entity_id,
    )

    return TimelineResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        events=[
            AuditLogResponse.model_validate(event)
            for event in events
        ],
        count=count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/user/{user_id}",
    response_model=TimelineResponse,
)
async def get_user_activity(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_service: AuditService = Depends(get_audit_service),
):
    events = await audit_service.get_user_activity(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    count = await audit_service.count_for_user(
        user_id=user_id,
    )

    return TimelineResponse(
        entity_type="user",
        entity_id=str(user_id),
        events=[
            AuditLogResponse.model_validate(event)
            for event in events
        ],
        count=count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/me",
    response_model=TimelineResponse,
)
async def get_my_activity(
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    events = await audit_service.get_user_activity(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    count = await audit_service.count_for_user(
        user_id=current_user.id,
    )

    return TimelineResponse(
        entity_type="user",
        entity_id=str(current_user.id),
        events=[
            AuditLogResponse.model_validate(event)
            for event in events
        ],
        count=count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/correlation/{correlation_id}",
    response_model=TimelineResponse,
)
async def get_correlation_events(
    correlation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_service: AuditService = Depends(get_audit_service),
):
    events = await audit_service.get_correlation_events(
        correlation_id=correlation_id,
        page=page,
        page_size=page_size,
    )

    count = await audit_service.count_for_correlation(
        correlation_id=correlation_id,
    )

    return TimelineResponse(
        entity_type="correlation",
        entity_id=str(correlation_id),
        events=[
            AuditLogResponse.model_validate(event)
            for event in events
        ],
        count=count,
        page=page,
        page_size=page_size,
    )