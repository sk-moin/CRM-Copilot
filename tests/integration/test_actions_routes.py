"""Route tests for the agent action approval API.

Every test here drives the real handler body. Feature 009 shipped two endpoints
that had never worked because their only verification was an OpenAPI schema
check and an anonymous 401 — neither of which executes the handler.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from app.services.agent_action_service import AgentActionService
from packages.database.models import Company
from packages.database.models.enums import AgentActionStatus


@pytest_asyncio.fixture
async def service(_async_session, seeded_user):
    return AgentActionService(session=_async_session, current_user=seeded_user)


@pytest_asyncio.fixture
async def company(_async_session, seeded_tenant, seeded_organization):
    company = Company(
        tenant_id=seeded_tenant.id,
        org_id=seeded_organization.id,
        name="Acme Corp",
    )
    _async_session.add(company)
    await _async_session.flush()

    return company


def _task_payload(user) -> dict:
    return {"title": "Follow up with Acme", "assigned_to_user_id": str(user.id)}


@pytest_asyncio.fixture
async def pending_action(service, seeded_user):
    return await service.propose(
        action_type="CREATE_TASK",
        payload=_task_payload(seeded_user),
        reason="The user asked to be reminded.",
    )


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_returns_pending_actions(authed_client, pending_action):
    response = await authed_client.get("api/v1/actions")

    assert response.status_code == 200, response.text

    body = response.json()
    ids = [item["id"] for item in body["items"]]

    assert str(pending_action.id) in ids
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_returns_the_action(authed_client, pending_action):
    response = await authed_client.get(f"api/v1/actions/{pending_action.id}")

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["action_type"] == "CREATE_TASK"
    assert body["status"] == AgentActionStatus.PENDING.value
    assert body["reason"] == "The user asked to be reminded."


@pytest.mark.asyncio
async def test_get_unknown_action_is_404(authed_client):
    response = await authed_client.get(f"api/v1/actions/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Action not found."


# --------------------------------------------------------------------------- #
# Decisions
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_approve_executes_and_reports_the_created_entity(
    authed_client,
    pending_action,
):
    response = await authed_client.post(
        f"api/v1/actions/{pending_action.id}/approve",
        json={"reason": "Looks right."},
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["status"] == AgentActionStatus.EXECUTED.value
    assert body["result_entity_type"] == "task"
    assert body["result_entity_id"]
    assert body["decision_reason"] == "Looks right."


@pytest.mark.asyncio
async def test_approving_twice_is_a_conflict_not_a_second_execution(
    authed_client,
    pending_action,
):
    """The rule the whole approval layer exists to guarantee."""

    first = await authed_client.post(
        f"api/v1/actions/{pending_action.id}/approve"
    )
    assert first.status_code == 200, first.text

    first_entity = first.json()["result_entity_id"]

    second = await authed_client.post(
        f"api/v1/actions/{pending_action.id}/approve"
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "This action has already been decided."

    # And the original result is untouched.
    check = await authed_client.get(f"api/v1/actions/{pending_action.id}")
    assert check.json()["result_entity_id"] == first_entity


@pytest.mark.asyncio
async def test_reject_decides_without_executing(authed_client, pending_action):
    response = await authed_client.post(
        f"api/v1/actions/{pending_action.id}/reject",
        json={"reason": "Not needed."},
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["status"] == AgentActionStatus.REJECTED.value
    assert body["result_entity_id"] is None
    assert body["executed_at"] is None


@pytest.mark.asyncio
async def test_rejecting_a_decided_action_is_a_conflict(
    authed_client,
    pending_action,
):
    await authed_client.post(f"api/v1/actions/{pending_action.id}/reject")

    second = await authed_client.post(
        f"api/v1/actions/{pending_action.id}/reject"
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_approve_unknown_action_is_404(authed_client):
    response = await authed_client.post(f"api/v1/actions/{uuid4()}/approve")

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "api/v1/actions"),
        ("get", "api/v1/actions/{id}"),
        ("post", "api/v1/actions/{id}/approve"),
        ("post", "api/v1/actions/{id}/reject"),
    ],
)
async def test_every_route_requires_authentication(client, method, path):
    url = path.format(id=uuid4())

    response = await getattr(client, method)(url)

    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# End to end: proposal -> approval -> real CRM row -> audit trail
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_proposal_through_approval_produces_the_crm_row_and_audit(
    authed_client,
    _async_session,
    seeded_tenant,
    seeded_user,
    service,
):
    """The whole point of the feature, in one pass."""

    from sqlalchemy import select

    from packages.database.models import AuditLog, Task

    action = await service.propose(
        action_type="CREATE_TASK",
        payload={
            "title": "Send the Acme renewal quote",
            "assigned_to_user_id": str(seeded_user.id),
        },
        reason="The user asked for a reminder.",
    )

    # Nothing in the CRM yet: proposing must not mutate.
    before = await _async_session.execute(
        select(Task).where(Task.title == "Send the Acme renewal quote")
    )
    assert before.scalars().first() is None

    response = await authed_client.post(f"api/v1/actions/{action.id}/approve")
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "EXECUTED"

    # The real row exists, tenant-scoped.
    created = await _async_session.execute(
        select(Task).where(Task.id == body["result_entity_id"])
    )
    task = created.scalars().one()

    assert task.title == "Send the Acme renewal quote"
    assert task.tenant_id == seeded_tenant.id

    # The audit trail tells the whole story under one correlation id.
    rows = await _async_session.execute(
        select(AuditLog).where(AuditLog.entity_id == action.id)
    )
    entries = list(rows.scalars().all())

    actors = [e.actor_type for e in entries]

    assert actors[0] == "AGENT", "the proposal is attributed to the agent"
    assert "USER" in actors, "the decision is attributed to a person"
    assert len({e.correlation_id for e in entries}) == 1


# --------------------------------------------------------------------------- #
# The propose node against the real service
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_propose_node_creates_one_pending_row_via_the_real_service(
    _async_session,
    seeded_user,
    service,
):
    """The node's unit tests use a stub that accepts anything and echoes back
    the kwargs they supplied, so they would still pass if the node and the
    real service were incompatible. This drives the real one."""

    from sqlalchemy import select

    from app.agent.nodes.propose import propose_node
    from packages.database.models.agent_action import AgentAction
    from packages.database.models.conversation import ConversationStatus
    from packages.database.repositories.conversation_repository import (
        ConversationRepository,
    )

    conversation = await ConversationRepository(
        session=_async_session,
        tenant_id=seeded_user.tenant_id,
    ).create(
        user_id=seeded_user.id,
        org_id=seeded_user.org_id,
        title="Proposal",
        status=ConversationStatus.ACTIVE,
    )
    conversation_id = conversation.id

    answer = (
        "I can set that up for you.\n\n"
        "```action\n"
        '{"action_type": "CREATE_TASK", "payload": '
        f'{{"title": "Call Acme back", "assigned_to_user_id": "{seeded_user.id}"}},'
        ' "reason": "You asked for a reminder."}\n'
        "```\n"
    )

    state = await propose_node(
        {"response": answer, "conversation_id": conversation_id, "errors": []},
        action_service_factory=lambda: service,
    )

    assert state["proposed_action_id"] is not None

    rows = await _async_session.execute(
        select(AgentAction).where(
            AgentAction.id == state["proposed_action_id"]
        )
    )
    action = rows.scalars().one()

    assert action.status == "PENDING"
    assert action.action_type == "CREATE_TASK"
    assert action.conversation_id == conversation_id
    assert action.payload["title"] == "Call Acme back"

    # The block is gone from what the user sees.
    assert "```action" not in state["response"]
    assert "I can set that up" in state["response"]


@pytest.mark.asyncio
async def test_propose_node_payload_the_real_schema_rejects_creates_nothing(
    _async_session,
    service,
):
    """A payload the node accepted but the service refuses must not create a
    row, and must not break the turn."""

    from sqlalchemy import func, select

    from app.agent.nodes.propose import propose_node
    from packages.database.models.agent_action import AgentAction

    before = await _async_session.execute(
        select(func.count()).select_from(AgentAction)
    )
    count_before = before.scalar_one()

    # No assigned_to_user_id: CreateTaskPayload requires it.
    answer = (
        "Sure.\n\n```action\n"
        '{"action_type": "CREATE_TASK", "payload": {"title": "Call Acme"}}\n```'
    )

    state = await propose_node(
        {"response": answer, "conversation_id": uuid4(), "errors": []},
        action_service_factory=lambda: service,
    )

    assert state["proposed_action_id"] is None
    assert state["response"]

    after = await _async_session.execute(
        select(func.count()).select_from(AgentAction)
    )
    assert after.scalar_one() == count_before
