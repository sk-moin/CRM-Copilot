#app/services/opportunity_service.py
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from packages.database.models.opportunity import Opportunity
from packages.database.repositories.company_repository import CompanyRepository
from packages.database.repositories.opportunity_repository import (
    OpportunityRepository,
)
from packages.database.repositories.user_repository import UserRepository


VALID_STAGES: Set[Literal[
    "LEAD",
    "QUALIFIED",
    "PROPOSAL",
    "NEGOTIATION",
    "WON",
    "LOST",
]] = {
    "LEAD",
    "QUALIFIED",
    "PROPOSAL",
    "NEGOTIATION",
    "WON",
    "LOST",
}


class OpportunityService:
    """
    Service layer for Opportunity CRUD operations.

    Repositories are tenant-scoped using
    current_user.organization.tenant_id.
    """

    def __init__(self, session: AsyncSession, current_user: Any):
        tenant_id = current_user.organization.tenant_id

        self.repo = OpportunityRepository(
            session=session,
            tenant_id=tenant_id,
        )

        self.company_repo = CompanyRepository(
            session=session,
            tenant_id=tenant_id,
        )

        self.user_repo = UserRepository(
            session=session,
            tenant_id=tenant_id,
        )

        self._org_id = current_user.org_id

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #

    async def create_opportunity(
        self,
        *,
        company_id: str,
        stage: str,
        title: str,
        value: Optional[Decimal] = None,
        owner_user_id: Optional[str] = None,
        probability: Optional[int] = None,
        expected_close_date: Optional[date] = None,
    ) -> Opportunity:
        """Create a new opportunity."""

        if not company_id:
            raise BusinessRuleViolationError("company_id is required")

        if not title:
            raise BusinessRuleViolationError("title is required")

        if not stage:
            raise BusinessRuleViolationError("stage is required")

        if stage not in VALID_STAGES:
            raise BusinessRuleViolationError(f"Invalid stage: {stage}")

        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundError(
                f"Company {company_id} not found"
            )

        if owner_user_id:
            owner = await self.user_repo.get_by_id(owner_user_id)
            if owner is None:
                raise EntityNotFoundError(
                    f"Owner {owner_user_id} not found"
                )

        if value is not None and value < 0:
            raise BusinessRuleViolationError(
                "value cannot be negative"
            )

        if probability is not None and not (0 <= probability <= 100):
            raise BusinessRuleViolationError(
                "probability must be between 0 and 100"
            )

        return await self.repo.create(
            company_id=company_id,
            org_id=self._org_id,
            stage=stage,
            title=title,
            value=value,
            owner_user_id=owner_user_id,
            probability=probability,
            expected_close_date=expected_close_date,
        )

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #

    async def get_opportunity(
        self,
        opportunity_id: str,
    ) -> Opportunity:
        """Retrieve a single opportunity."""

        opportunity = await self.repo.get_by_id(
            opportunity_id
        )

        if opportunity is None:
            raise EntityNotFoundError(
                f"Opportunity {opportunity_id} not found"
            )

        return opportunity

    async def list_opportunities(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Opportunity]:
        """List opportunities with optional filters."""

        return await self.repo.list(**(filters or {}))

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #

    async def update_opportunity(
        self,
        opportunity_id: str,
        *,
        stage: Optional[str] = None,
        title: Optional[str] = None,
        value: Optional[Decimal] = None,
        owner_user_id: Optional[str] = None,
        probability: Optional[int] = None,
        expected_close_date: Optional[date] = None,
    ) -> Opportunity:
        """Update an opportunity."""

        existing = await self.get_opportunity(
            opportunity_id
        )

        update_data: Dict[str, Any] = {}

        if stage is not None:
            if stage not in VALID_STAGES:
                raise BusinessRuleViolationError(
                    f"Invalid stage: {stage}"
                )

            update_data["stage"] = stage

        if title is not None:
            update_data["title"] = title

        if value is not None:
            if value < 0:
                raise BusinessRuleViolationError(
                    "value cannot be negative"
                )

            update_data["value"] = value

        if probability is not None:
            if not (0 <= probability <= 100):
                raise BusinessRuleViolationError(
                    "probability must be between 0 and 100"
                )

            update_data["probability"] = probability

        if expected_close_date is not None:
            update_data["expected_close_date"] = (
                expected_close_date
            )

        if owner_user_id is not None:
            owner = await self.user_repo.get_by_id(
                owner_user_id
            )

            if owner is None:
                raise EntityNotFoundError(
                    f"Owner {owner_user_id} not found"
                )

            update_data["owner_user_id"] = owner_user_id

        if not update_data:
            return existing

        updated = await self.repo.update(
            opportunity_id,
            **update_data,
        )

        if updated is None:
            raise EntityNotFoundError(
                f"Opportunity {opportunity_id} not found"
            )

        return updated

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #

    async def delete_opportunity(
        self,
        opportunity_id: str,
    ) -> bool:
        """Delete an opportunity."""

        await self.get_opportunity(opportunity_id)

        return await self.repo.delete(opportunity_id)

    # ------------------------------------------------------------------ #
    # BUSINESS HELPERS
    # ------------------------------------------------------------------ #

    async def change_stage(
        self,
        opportunity_id: str,
        new_stage: str,
    ) -> Opportunity:
        """Change opportunity stage."""

        await self.get_opportunity(opportunity_id)

        if new_stage not in VALID_STAGES:
            raise BusinessRuleViolationError(
                f"Invalid stage: {new_stage}"
            )

        updated = await self.repo.update(
            opportunity_id,
            stage=new_stage,
        )

        if updated is None:
            raise EntityNotFoundError(
                f"Opportunity {opportunity_id} not found"
            )

        return updated

    async def assign_owner(
        self,
        opportunity_id: str,
        new_owner_id: str,
    ) -> Opportunity:
        """Assign a new owner."""

        await self.get_opportunity(opportunity_id)

        owner = await self.user_repo.get_by_id(
            new_owner_id
        )

        if owner is None:
            raise EntityNotFoundError(
                f"Owner {new_owner_id} not found"
            )

        updated = await self.repo.update(
            opportunity_id,
            owner_user_id=new_owner_id,
        )

        if updated is None:
            raise EntityNotFoundError(
                f"Opportunity {opportunity_id} not found"
            )

        return updated