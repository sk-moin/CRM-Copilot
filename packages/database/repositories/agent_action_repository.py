"""Repository for agent-proposed CRM actions.

Tenant scoping comes from `BaseRepository`, which force-sets `tenant_id` on
create and pops it on update, so this class never reimplements the filter.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select

from packages.database.models.agent_action import AgentAction
from packages.database.models.enums import AgentActionStatus
from packages.database.repositories.base_repository import BaseRepository


class AgentActionRepository(BaseRepository):
    """Tenant-scoped access to `agent_action`."""

    model = AgentAction

    async def list_pending(
        self,
        org_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentAction]:
        """Return undecided actions, oldest first.

        Oldest-first because this is an approval queue: the thing waiting
        longest should surface first.
        """

        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.status == AgentActionStatus.PENDING.value,
        )

        if org_id is not None:
            stmt = stmt.where(self.model.org_id == org_id)

        stmt = stmt.order_by(self.model.created_at.asc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: AgentActionStatus,
        org_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentAction]:
        """Return actions in one status, oldest first.

        Same ordering as `list_pending`: one endpoint returning newest-first or
        oldest-first depending on whether `?status=` was supplied is a trap for
        anyone paging through it.
        """

        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.status == status.value,
        )

        if org_id is not None:
            stmt = stmt.where(self.model.org_id == org_id)

        stmt = stmt.order_by(self.model.created_at.asc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def get_for_org(
        self,
        action_id: Any,
        org_id: UUID,
    ) -> Optional[AgentAction]:
        """Read one action, scoped to tenant AND org.

        `BaseRepository.get_by_id` scopes to the tenant only. Reads here must
        also match the org, or a user in one org can see and act on another
        org's queue while `list_pending` hides it from them.
        """

        stmt = select(self.model).where(
            self.model.id == action_id,
            self.model.tenant_id == self.tenant_id,
            self.model.org_id == org_id,
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def claim_pending(
        self,
        action_id: Any,
        org_id: UUID,
    ) -> Optional[AgentAction]:
        """Lock a PENDING action for decision, or return None.

        `SELECT ... FOR UPDATE` on the row, filtered by status, so two
        concurrent approvals cannot both pass the check and execute the
        mutation twice. The caller decides within the same transaction.

        Scoped to org as well as tenant: the executor stamps the CRM row with
        the approver's org, so approving across orgs would file the result
        where the proposing org cannot see it.
        """

        stmt = (
            select(self.model)
            .where(
                self.model.id == action_id,
                self.model.tenant_id == self.tenant_id,
                self.model.org_id == org_id,
                self.model.status == AgentActionStatus.PENDING.value,
            )
            .with_for_update()
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()
