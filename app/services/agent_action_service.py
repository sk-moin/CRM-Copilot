"""Lifecycle of agent-proposed CRM actions.

The rule this service exists to enforce: the agent never mutates the CRM. It
proposes, a human decides, and only an approved proposal executes — exactly
once. Every transition writes to the feature 003 audit trail, with `actor_type`
separating the agent's proposal from the human's decision and a shared
`correlation_id` joining them.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_actions.executors import executor_for
from app.services.agent_actions.payloads import schema_for
from app.services.audit_service import AuditService
from packages.database.models.agent_action import AgentAction
from packages.database.models.audit import AuditAction
from packages.database.models.enums import AgentActionStatus, AgentActionType
from packages.database.repositories.agent_action_repository import (
    AgentActionRepository,
)

logger = logging.getLogger(__name__)

ENTITY_TYPE = "agent_action"


class AgentActionError(Exception):
    """Base for expected, caller-visible action failures."""


class ActionNotFoundError(AgentActionError):
    """No such action in this tenant."""


class ActionNotPendingError(AgentActionError):
    """Already decided. Deciding again is refused, never re-executed."""


class InvalidActionPayloadError(AgentActionError):
    """The payload does not match its type's schema."""


class UnsupportedActionTypeError(AgentActionError):
    """The type is not on the allow-list."""


class AgentActionService:
    """Owns propose, approve, reject and execution."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: Any,
    ) -> None:
        self._session = session
        self._user = current_user
        self._tenant_id = current_user.tenant_id

        self._repo = AgentActionRepository(
            session=session,
            tenant_id=self._tenant_id,
        )

        self._audit = AuditService(
            session=session,
            tenant_id=self._tenant_id,
            current_user=current_user,
        )

    # ------------------------------------------------------------------ #
    # Propose
    # ------------------------------------------------------------------ #

    async def propose(
        self,
        *,
        action_type: str,
        payload: dict,
        reason: Optional[str] = None,
        conversation_id: Optional[UUID] = None,
    ) -> AgentAction:
        """Record a proposal. Writes nothing to the CRM.

        Validates here as well as at execution so a malformed proposal is
        refused at the point it is made, while the stored row is always one
        that could in principle execute.
        """

        resolved_type = self._resolve_type(action_type)
        validated = self._validate_payload(resolved_type, payload)

        # Savepoint: propose is called from inside a chat turn, before the
        # assistant message is written. A failure that reaches a flush here
        # would abort the surrounding transaction and cost the user their
        # answer and their own message, which the propose node's caller
        # cannot recover from by catching the exception alone.
        async with self._session.begin_nested():
            action = await self._repo.create(
                org_id=self._user.org_id,
                conversation_id=conversation_id,
                proposed_by_user_id=self._user.id,
                action_type=resolved_type.value,
                payload=validated,
                reason=reason,
                status=AgentActionStatus.PENDING.value,
            )

        await self._audit.log_event(
            action=AuditAction.CREATE,
            entity_type=ENTITY_TYPE,
            entity_id=action.id,
            org_id=self._user.org_id,
            after_values={
                "action_type": resolved_type.value,
                "status": AgentActionStatus.PENDING.value,
            },
            # The agent proposed this, not the user whose turn it was.
            actor_type="AGENT",
            correlation_id=action.correlation_id,
            event_metadata={"conversation_id": str(conversation_id)}
            if conversation_id
            else None,
        )

        return action

    # ------------------------------------------------------------------ #
    # Decisions
    # ------------------------------------------------------------------ #

    async def reject(
        self,
        action_id: UUID,
        reason: Optional[str] = None,
    ) -> AgentAction:
        """Decline a pending proposal. The CRM is never touched."""

        action = await self._claim(action_id)

        return await self._decide(
            action,
            status=AgentActionStatus.REJECTED,
            reason=reason,
        )

    async def approve(
        self,
        action_id: UUID,
        reason: Optional[str] = None,
    ) -> AgentAction:
        """Approve a pending proposal and execute it.

        `claim_pending` takes a row lock filtered by PENDING, so two concurrent
        approvals cannot both pass the check. The loser gets
        ActionNotPendingError rather than a second execution.
        """

        action = await self._claim(action_id)

        await self._decide(
            action,
            status=AgentActionStatus.APPROVED,
            reason=reason,
        )

        return await self._execute(action)

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    async def list_actions(
        self,
        status: Optional[AgentActionStatus] = None,
    ) -> list[AgentAction]:
        if status is None:
            return await self._repo.list_pending(org_id=self._user.org_id)

        return await self._repo.list_by_status(status, org_id=self._user.org_id)

    async def get_action(self, action_id: UUID) -> AgentAction:
        action = await self._repo.get_for_org(action_id, self._user.org_id)

        if action is None:
            raise ActionNotFoundError(str(action_id))

        return action

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _resolve_type(self, action_type: str) -> AgentActionType:
        try:
            return AgentActionType(action_type)
        except ValueError as exc:
            raise UnsupportedActionTypeError(str(action_type)) from exc

    def _validate_payload(
        self,
        action_type: AgentActionType,
        payload: dict,
    ) -> dict:
        try:
            schema = schema_for(action_type)
        except KeyError as exc:
            raise UnsupportedActionTypeError(action_type.value) from exc

        try:
            model = schema.model_validate(payload or {})
        except ValidationError as exc:
            raise InvalidActionPayloadError(str(exc)) from exc

        # JSON-safe, so UUIDs survive the JSONB round trip.
        return model.model_dump(mode="json", exclude_none=True)

    async def _claim(self, action_id: UUID) -> AgentAction:
        action = await self._repo.claim_pending(action_id, self._user.org_id)

        if action is not None:
            return action

        # Distinguish "not yours / no such action" from "already decided", so
        # another tenant's or another org's row is a 404, not a 409 that would
        # confirm it exists.
        if await self._repo.get_for_org(action_id, self._user.org_id) is None:
            raise ActionNotFoundError(str(action_id))

        raise ActionNotPendingError(str(action_id))

    async def _decide(
        self,
        action: AgentAction,
        *,
        status: AgentActionStatus,
        reason: Optional[str],
    ) -> AgentAction:
        before = {"status": action.status}

        action.status = status.value
        action.decided_by_user_id = self._user.id
        action.decided_at = datetime.now(UTC)
        action.decision_reason = reason

        await self._session.flush()
        await self._session.refresh(action)

        await self._audit.log_event(
            action=AuditAction.UPDATE,
            entity_type=ENTITY_TYPE,
            entity_id=action.id,
            org_id=action.org_id,
            before_values=before,
            after_values={"status": status.value},
            # A person decided, whoever proposed it.
            actor_type="USER",
            correlation_id=action.correlation_id,
        )

        return action

    async def _execute(self, action: AgentAction) -> AgentAction:
        action_type = AgentActionType(action.action_type)

        try:
            handler = executor_for(action_type)
            payload = self._validate_payload(action_type, action.payload)
            model = schema_for(action_type).model_validate(payload)

            # Savepoint, not a bare call. A handler that fails inside a
            # flush aborts the surrounding transaction, which would take the
            # FAILED write and its audit entry down with it — the recovery
            # block below would raise instead of running, the request would
            # 500, and the action would silently revert to PENDING and
            # reappear in the queue forever.
            async with self._session.begin_nested():
                entity_type, entity_id = await handler(
                    self._session,
                    self._user,
                    model,
                )

        except Exception as exc:
            # The CRM write and this status write share the caller's
            # transaction, so a failed handler leaves no partial mutation.
            logger.exception(
                "agent_action.execution_failed",
                extra={"action_id": str(action.id), "type": action.action_type},
            )

            action.status = AgentActionStatus.FAILED.value
            # The class name only. This field is returned to API clients, and
            # str(exc) would carry SQL, column names and entity ids. The full
            # detail is in the server log above.
            action.error_message = type(exc).__name__

            await self._session.flush()
            await self._session.refresh(action)

            await self._audit.log_event(
                action=AuditAction.UPDATE,
                entity_type=ENTITY_TYPE,
                entity_id=action.id,
                org_id=action.org_id,
                after_values={"status": AgentActionStatus.FAILED.value},
                actor_type="USER",
                correlation_id=action.correlation_id,
            )

            return action

        action.status = AgentActionStatus.EXECUTED.value
        action.executed_at = datetime.now(UTC)
        action.result_entity_type = entity_type
        action.result_entity_id = entity_id
        action.error_message = None

        await self._session.flush()
        await self._session.refresh(action)

        await self._audit.log_event(
            action=AuditAction.UPDATE,
            entity_type=ENTITY_TYPE,
            entity_id=action.id,
            org_id=action.org_id,
            after_values={
                "status": AgentActionStatus.EXECUTED.value,
                "result_entity_type": entity_type,
                "result_entity_id": str(entity_id),
            },
            actor_type="USER",
            correlation_id=action.correlation_id,
        )

        return action
