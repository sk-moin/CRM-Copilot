"""Approval API for agent-proposed CRM actions.

Thin handlers. The service owns the lifecycle and the tenant scope; these
translate its expected errors into status codes and never return internal
detail, following the convention set in feature 009.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_agent_action_service
from app.api.schemas.actions import (
    ActionDecisionRequest,
    AgentActionListResponse,
    AgentActionResponse,
)
from app.services.agent_action_service import (
    ActionNotFoundError,
    ActionNotPendingError,
    AgentActionService,
)
from packages.database.models.enums import AgentActionStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/actions",
    tags=["AI Actions"],
)


@router.get("", response_model=AgentActionListResponse)
async def list_actions(
    action_status: Optional[AgentActionStatus] = Query(
        default=None,
        alias="status",
        description="Defaults to pending when omitted.",
    ),
    service: AgentActionService = Depends(get_agent_action_service),
) -> AgentActionListResponse:
    """List proposed actions. Pending by default, since this is a queue."""

    actions = await service.list_actions(status=action_status)

    return AgentActionListResponse(
        items=[AgentActionResponse.model_validate(a) for a in actions],
        total=len(actions),
    )


@router.get("/{action_id}", response_model=AgentActionResponse)
async def get_action(
    action_id: UUID,
    service: AgentActionService = Depends(get_agent_action_service),
) -> AgentActionResponse:
    try:
        action = await service.get_action(action_id)
    except ActionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found.",
        ) from None

    return AgentActionResponse.model_validate(action)


@router.post("/{action_id}/approve", response_model=AgentActionResponse)
async def approve_action(
    action_id: UUID,
    request: ActionDecisionRequest | None = None,
    service: AgentActionService = Depends(get_agent_action_service),
) -> AgentActionResponse:
    """Approve and execute a pending action.

    A second approve is a 409, never a second execution.
    """

    try:
        action = await service.approve(
            action_id,
            reason=request.reason if request else None,
        )

    except ActionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found.",
        ) from None

    except ActionNotPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This action has already been decided.",
        ) from None

    except Exception as exc:
        logger.exception("actions.approve.failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve the action.",
        ) from exc

    return AgentActionResponse.model_validate(action)


@router.post("/{action_id}/reject", response_model=AgentActionResponse)
async def reject_action(
    action_id: UUID,
    request: ActionDecisionRequest | None = None,
    service: AgentActionService = Depends(get_agent_action_service),
) -> AgentActionResponse:
    try:
        action = await service.reject(
            action_id,
            reason=request.reason if request else None,
        )

    except ActionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found.",
        ) from None

    except ActionNotPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This action has already been decided.",
        ) from None

    except Exception as exc:
        logger.exception("actions.reject.failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject the action.",
        ) from exc

    return AgentActionResponse.model_validate(action)
