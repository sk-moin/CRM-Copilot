from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.task import Task
from packages.database.repositories.task_repository import TaskRepository
from packages.database.repositories.user_repository import UserRepository
from packages.database.repositories.company_repository import CompanyRepository
from packages.database.repositories.contact_repository import ContactRepository
from packages.database.repositories.opportunity_repository import (
    OpportunityRepository,
)

from app.services.audit_service import AuditService
from app.services.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
)


class TaskService:
    """
    Service layer for Task CRUD operations.
    """

    def __init__(
        self,
        session: AsyncSession,
        current_user: Any,
    ):
        self._session = session
        self._user = current_user
        self.tenant_id = current_user.tenant_id

        self.repo = TaskRepository(
            session=session,
            tenant_id=self.tenant_id,
        )

        self.user_repo = UserRepository(
            session=session,
            tenant_id=self.tenant_id,
        )

        self.company_repo = CompanyRepository(
            session=session,
            tenant_id=self.tenant_id,
        )

        self.contact_repo = ContactRepository(
            session=session,
            tenant_id=self.tenant_id,
        )

        self.opportunity_repo = OpportunityRepository(
            session=session,
            tenant_id=self.tenant_id,
        )

        self.audit_service = AuditService(
            session=session,
            tenant_id=self.tenant_id,
            current_user=current_user,
        )

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #

    async def create_task(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        status: str = "PENDING",
        priority: str = "MEDIUM",
        due_date: Optional[Any] = None,
        assigned_to_user_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Task:

        if not title or not title.strip():
            raise BusinessRuleViolationError(
                "title is required"
            )

        assignee = await self.user_repo.get_by_id(
            assigned_to_user_id
        )

        if assignee is None:
            raise EntityNotFoundError(
                f"User {assigned_to_user_id} not found"
            )

        if (entity_type is None) ^ (entity_id is None):
            raise BusinessRuleViolationError(
                "entity_type and entity_id must both be set or both be omitted"
            )

        if entity_type is not None:
            repo_map = {
                "company": self.company_repo,
                "contact": self.contact_repo,
                "opportunity": self.opportunity_repo,
            }

            repo = repo_map.get(entity_type)

            if repo is None:
                raise BusinessRuleViolationError(
                    f"Invalid entity_type: {entity_type}"
                )

            entity = await repo.get_by_id(entity_id)

            if entity is None:
                raise EntityNotFoundError(
                    f"{entity_type.title()} {entity_id} not found"
                )

        task = await self.repo.create(
            title=title.strip(),
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            assigned_to_user_id=assigned_to_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            org_id=self._user.org_id,
        )

        await self.audit_service.log_create(
            entity_type="task",
            entity_id=task.id,
            after_values=self.audit_service.build_task_snapshot(
                task
            ),
        )

        return task

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #

    async def get_task(
        self,
        task_id: str,
    ) -> Task:

        task = await self.repo.get_by_id(task_id)

        if task is None:
            raise EntityNotFoundError(
                f"Task {task_id} not found"
            )

        return task

    async def list_tasks(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Task]:

        return await self.repo.list(
            **(filters or {})
        )


        # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #

    async def update_task(
        self,
        task_id: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[Any] = None,
        assigned_to_user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Task:
        """Update an existing task."""

        task = await self.get_task(task_id)

        before_snapshot = self.audit_service.build_task_snapshot(task)

        # --------------------------------------------------------------
        # Validate assigned user if the field is being changed
        # --------------------------------------------------------------
        if assigned_to_user_id is not None:
            assignee = await self.user_repo.get_by_id(assigned_to_user_id)
            if assignee is None:
                raise EntityNotFoundError(
                    f"User {assigned_to_user_id} not found"
                )

        # --------------------------------------------------------------
        # Validate polymorphic attachment consistency
        # --------------------------------------------------------------
        if (entity_type is None) ^ (entity_id is None):
            raise BusinessRuleViolationError(
                "entity_type and entity_id must both be set or both be omitted"
            )

        if entity_type is not None:
            repo_map = {
                "company": self.company_repo,
                "contact": self.contact_repo,
                "opportunity": self.opportunity_repo,
            }

            repo = repo_map.get(entity_type)
            if repo is None:
                raise BusinessRuleViolationError(
                    f"Invalid entity_type: {entity_type}"
                )

            entity = await repo.get_by_id(entity_id)
            if entity is None:
                raise EntityNotFoundError(
                    f"{entity_type.title()} {entity_id} not found"
                )

        update_data: Dict[str, Any] = {}

        if title is not None:
            update_data["title"] = title.strip()

        if description is not None:
            update_data["description"] = description

        if status is not None:
            update_data["status"] = status

        if priority is not None:
            update_data["priority"] = priority

        if due_date is not None:
            update_data["due_date"] = due_date

        if assigned_to_user_id is not None:
            update_data["assigned_to_user_id"] = assigned_to_user_id

        if entity_type is not None:
            update_data["entity_type"] = entity_type
            update_data["entity_id"] = entity_id

        if not update_data:
            return task

        updated = await self.repo.update(
            task_id,
            **update_data,
        )

        if updated is None:
            raise EntityNotFoundError(
                f"Task {task_id} not found after update"
            )

        await self.audit_service.log_update(
            entity_type="task",
            entity_id=updated.id,
            before_values=before_snapshot,
            after_values=self.audit_service.build_task_snapshot(updated),
        )

        return updated

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #

    async def delete_task(
        self,
        task_id: str,
    ) -> bool:
        """Delete a task."""

        task = await self.get_task(task_id)

        before_snapshot = self.audit_service.build_task_snapshot(task)

        deleted = await self.repo.delete(task_id)

        if deleted:
            await self.audit_service.log_delete(
                entity_type="task",
                entity_id=task.id,
                before_values=before_snapshot,
            )

        return deleted