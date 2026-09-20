"""Execution handlers for approved agent actions.

One handler per action type, each calling a named CRM service method. The
mapping is a literal dict: there is no path from a payload value to a method
name, so a malformed or hostile proposal cannot reach a method nobody intended
to expose.

Each handler returns `(entity_type, entity_id)` so the action can record what
it actually produced.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_actions.payloads import (
    CreateContactPayload,
    CreateTaskPayload,
    UpdateContactPayload,
    UpdateOpportunityStagePayload,
    UpdateTaskStatusPayload,
)
from app.services.contact_service import ContactService
from app.services.opportunity_service import OpportunityService
from app.services.task_service import TaskService
from packages.database.models.enums import AgentActionType

ExecutionResult = tuple[str, UUID]


async def _create_task(
    session: AsyncSession,
    user: Any,
    payload: CreateTaskPayload,
) -> ExecutionResult:
    service = TaskService(session=session, current_user=user)

    task = await service.create_task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assigned_to_user_id=str(payload.assigned_to_user_id),
        entity_type=payload.entity_type,
        entity_id=str(payload.entity_id) if payload.entity_id else None,
    )

    return "task", task.id


async def _update_task_status(
    session: AsyncSession,
    user: Any,
    payload: UpdateTaskStatusPayload,
) -> ExecutionResult:
    service = TaskService(session=session, current_user=user)

    task = await service.update_task(
        str(payload.task_id),
        status=payload.status,
    )

    return "task", task.id


async def _create_contact(
    session: AsyncSession,
    user: Any,
    payload: CreateContactPayload,
) -> ExecutionResult:
    service = ContactService(session=session, current_user=user)

    contact = await service.create_contact(
        first_name=payload.first_name,
        last_name=payload.last_name,
        company_id=str(payload.company_id),
        email=payload.email,
        phone=payload.phone,
        job_title=payload.job_title,
    )

    return "contact", contact.id


async def _update_contact(
    session: AsyncSession,
    user: Any,
    payload: UpdateContactPayload,
) -> ExecutionResult:
    service = ContactService(session=session, current_user=user)

    contact = await service.update_contact(
        str(payload.contact_id),
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        job_title=payload.job_title,
    )

    return "contact", contact.id


async def _update_opportunity_stage(
    session: AsyncSession,
    user: Any,
    payload: UpdateOpportunityStagePayload,
) -> ExecutionResult:
    service = OpportunityService(session=session, current_user=user)

    opportunity = await service.change_stage(
        str(payload.opportunity_id),
        payload.stage,
    )

    return "opportunity", opportunity.id


Handler = Callable[[AsyncSession, Any, Any], Awaitable[ExecutionResult]]

EXECUTORS: dict[AgentActionType, Handler] = {
    AgentActionType.CREATE_TASK: _create_task,
    AgentActionType.UPDATE_TASK_STATUS: _update_task_status,
    AgentActionType.CREATE_CONTACT: _create_contact,
    AgentActionType.UPDATE_CONTACT: _update_contact,
    AgentActionType.UPDATE_OPPORTUNITY_STAGE: _update_opportunity_stage,
}
"""The allow-list. Adding a capability means adding a line here on purpose."""


def executor_for(action_type: AgentActionType) -> Handler:
    """Return the handler for a type, or raise for an unsupported one."""

    handler = EXECUTORS.get(action_type)

    if handler is None:
        raise KeyError(f"No executor for action type {action_type!r}.")

    return handler
