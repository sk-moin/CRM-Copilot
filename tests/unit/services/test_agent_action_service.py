"""Lifecycle rules for agent-proposed CRM actions.

The rules under test are the ones that make an approval layer worth having:
proposing writes nothing to the CRM, only PENDING can be decided, an action
executes at most once, and every transition is audited with the right actor.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.services.agent_action_service import (
    ActionNotFoundError,
    ActionNotPendingError,
    AgentActionService,
    InvalidActionPayloadError,
    UnsupportedActionTypeError,
)
from packages.database.models import AuditLog, Company
from packages.database.models.agent_action import AgentAction
from packages.database.models.enums import AgentActionStatus, AgentActionType
from packages.database.repositories.agent_action_repository import (
    AgentActionRepository,
)


@pytest_asyncio.fixture
async def service(async_session, user):
    return AgentActionService(session=async_session, current_user=user)


@pytest_asyncio.fixture
async def company(async_session, tenant, organization):
    company = Company(
        tenant_id=tenant.id,
        org_id=organization.id,
        name="Acme Corp",
    )
    async_session.add(company)
    await async_session.flush()

    return company


def _task_payload(user) -> dict:
    return {"title": "Follow up with Acme", "assigned_to_user_id": str(user.id)}


async def _audit_rows(async_session, action_id):
    result = await async_session.execute(
        select(AuditLog).where(AuditLog.entity_id == action_id)
    )

    return list(result.scalars().all())


# --------------------------------------------------------------------------- #
# Propose
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_propose_records_pending_and_touches_no_crm(
    service,
    async_session,
    tenant,
    user,
):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
        reason="The user asked to be reminded.",
    )

    assert action.status == AgentActionStatus.PENDING.value
    assert action.proposed_by_user_id == user.id
    assert action.decided_by_user_id is None

    # Nothing executed, so nothing was produced.
    assert action.result_entity_id is None
    assert action.executed_at is None


@pytest.mark.asyncio
async def test_propose_is_audited_as_the_agent(service, async_session, user):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    rows = await _audit_rows(async_session, action.id)

    assert len(rows) == 1
    assert rows[0].actor_type == "AGENT"
    assert rows[0].correlation_id == action.correlation_id


@pytest.mark.asyncio
async def test_unsupported_type_is_refused(service, user):
    with pytest.raises(UnsupportedActionTypeError):
        await service.propose(
            action_type="DELETE_ALL_COMPANIES",
            payload={},
        )


@pytest.mark.asyncio
async def test_malformed_payload_is_refused(service):
    with pytest.raises(InvalidActionPayloadError):
        await service.propose(
            action_type="CREATE_TASK",
            payload={"title": "no assignee"},
        )


@pytest.mark.asyncio
async def test_unexpected_payload_key_is_refused(service, user):
    """Strict schemas: an extra key is a refusal, not a silent drop."""

    payload = _task_payload(user) | {"tenant_id": str(uuid4())}

    with pytest.raises(InvalidActionPayloadError):
        await service.propose(action_type="CREATE_TASK", payload=payload)


# --------------------------------------------------------------------------- #
# Decisions
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_reject_decides_without_executing(service, async_session, user):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    rejected = await service.reject(action.id, reason="Not needed.")

    assert rejected.status == AgentActionStatus.REJECTED.value
    assert rejected.decided_by_user_id == user.id
    assert rejected.decision_reason == "Not needed."
    assert rejected.executed_at is None


@pytest.mark.asyncio
async def test_decision_is_audited_as_the_user(service, async_session, user):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )
    await service.reject(action.id)

    rows = await _audit_rows(async_session, action.id)
    actors = [r.actor_type for r in rows]

    assert actors == ["AGENT", "USER"]
    # One correlation id ties the proposal to its outcome.
    assert len({r.correlation_id for r in rows}) == 1


@pytest.mark.asyncio
async def test_approve_executes_and_produces_the_real_row(
    service,
    async_session,
    user,
):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    executed = await service.approve(action.id)

    assert executed.status == AgentActionStatus.EXECUTED.value
    assert executed.result_entity_type == "task"
    assert executed.result_entity_id is not None
    assert executed.executed_at is not None


@pytest.mark.asyncio
async def test_a_decided_action_cannot_be_decided_again(
    service,
    async_session,
    user,
):
    """The guard that stops a double-approve executing twice."""

    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    await service.approve(action.id)

    with pytest.raises(ActionNotPendingError):
        await service.approve(action.id)

    with pytest.raises(ActionNotPendingError):
        await service.reject(action.id)


@pytest.mark.asyncio
async def test_rejected_action_cannot_later_be_approved(service, user):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    await service.reject(action.id)

    with pytest.raises(ActionNotPendingError):
        await service.approve(action.id)


@pytest.mark.asyncio
async def test_missing_action_is_not_found(service):
    with pytest.raises(ActionNotFoundError):
        await service.approve(uuid4())


# --------------------------------------------------------------------------- #
# Execution failure
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_handler_failing_before_any_write_marks_failed(
    service,
    async_session,
    user,
):
    """Pre-flush failure: the target row does not exist."""

    from packages.database.models import Task

    action = await service.propose(
        action_type="UPDATE_TASK_STATUS",
        payload={"task_id": str(uuid4()), "status": "COMPLETED"},
    )

    result = await service.approve(action.id)

    assert result.status == AgentActionStatus.FAILED.value
    assert result.error_message
    assert result.result_entity_id is None

    # The assertion the old version of this test promised and never made.
    rows = await async_session.execute(select(Task))
    assert rows.scalars().all() == []


@pytest.mark.asyncio
async def test_a_handler_failing_during_flush_still_marks_failed(
    service,
    async_session,
    user,
    monkeypatch,
):
    """Failure *inside* a flush is the case that breaks the recovery block.

    A DB-level error aborts the transaction, so without a savepoint the FAILED
    write and its audit entry raise too: the request 500s, no record is kept,
    and the action silently reverts to PENDING to fail again forever.

    Reaching this through the real allow-list is not possible: every handler
    resolves its foreign keys through a tenant-scoped repository first, so a
    bad id fails *before* any flush. An earlier version of this test used such
    a payload, which made it a duplicate of the pre-flush case above — it
    passed with the savepoint removed. The handler is substituted here so the
    failure genuinely happens mid-flush.
    """

    from packages.database.models import Task
    from packages.database.models.enums import AgentActionType
    from app.services.agent_actions import executors

    async def _writes_then_violates_a_fk(session, current_user, payload):
        session.add(
            Task(
                tenant_id=current_user.tenant_id,
                org_id=current_user.org_id,
                title="never committed",
                assigned_to_user_id=uuid4(),  # no such user
                status="PENDING",
                priority="MEDIUM",
            )
        )
        await session.flush()

        return "task", uuid4()

    monkeypatch.setitem(
        executors.EXECUTORS,
        AgentActionType.CREATE_TASK,
        _writes_then_violates_a_fk,
    )

    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )

    result = await service.approve(action.id)

    assert result.status == AgentActionStatus.FAILED.value
    assert result.error_message
    assert result.result_entity_id is None

    # The half-written row is gone with the savepoint.
    rows = await async_session.execute(select(Task))
    assert rows.scalars().all() == []

    # The failure itself is audited, and the session survives to do it.
    audit = await _audit_rows(async_session, action.id)
    assert [r.actor_type for r in audit] == ["AGENT", "USER", "USER"]

    # Still usable afterwards: without the savepoint this would raise.
    await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )


@pytest.mark.asyncio
async def test_a_failing_propose_leaves_the_session_usable(
    service,
    async_session,
    user,
):
    """propose runs mid-chat-turn, before the assistant message is written.

    Without a savepoint a flush-level failure here aborts the surrounding
    transaction, and the later message write raises PendingRollbackError: the
    user loses their answer and their own message to a 500.
    """

    from packages.database.models.conversation import Conversation

    with pytest.raises(Exception):
        await service.propose(
            action_type="CREATE_TASK",
            payload=_task_payload(user),
            conversation_id=uuid4(),  # no such conversation: FK violation
        )

    # The caller can still write. This is the assertion that fails without
    # the savepoint.
    async_session.add(
        Conversation(
            tenant_id=user.tenant_id,
            org_id=user.org_id,
            user_id=user.id,
            title="written after the failure",
            status="active",
        )
    )
    await async_session.flush()


@pytest.mark.asyncio
async def test_error_message_does_not_leak_internal_detail(service, user):
    """error_message is returned by the API, so it carries no str(exc)."""

    action = await service.propose(
        action_type="CREATE_TASK",
        payload={"title": "fk violation", "assigned_to_user_id": str(uuid4())},
    )

    result = await service.approve(action.id)

    # An exception class name, not SQL or entity ids.
    assert chr(10) not in result.error_message
    assert "SELECT" not in result.error_message.upper()
    assert "INSERT" not in result.error_message.upper()
    assert len(result.error_message) < 100


@pytest.mark.asyncio
async def test_an_out_of_range_status_is_refused_before_the_database(service):
    """"DONE" is the most natural status an LLM emits, and is not a member."""

    with pytest.raises(InvalidActionPayloadError):
        await service.propose(
            action_type="UPDATE_TASK_STATUS",
            payload={"task_id": str(uuid4()), "status": "DONE"},
        )


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_defaults_to_pending(service, async_session, user):
    pending = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )
    decided = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )
    await service.reject(decided.id)

    ids = [a.id for a in await service.list_actions()]

    assert pending.id in ids
    assert decided.id not in ids


@pytest.mark.asyncio
async def test_list_can_filter_by_status(service, user):
    action = await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(user),
    )
    await service.reject(action.id)

    ids = [
        a.id
        for a in await service.list_actions(status=AgentActionStatus.REJECTED)
    ]

    assert action.id in ids
