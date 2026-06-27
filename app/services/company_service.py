from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import company
from packages.database.models.company import Company
from packages.database.repositories.company_repository import CompanyRepository
from app.services.audit_service import AuditService
from app.services.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
)


class CompanyService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: Any,
    ):
        self._session = session
        self._user = current_user
        self.tenant_id = current_user.tenant_id

        self.repo = CompanyRepository(
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

    async def create_company(
        self,
        *,
        name: str,
        industry: Optional[str] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Company:
        if not name or not name.strip():
            raise BusinessRuleViolationError(
                "Company name is required"
            )

        name = name.strip()

        existing = await self.repo.list(name=name)

        if existing:
            raise BusinessRuleViolationError(
                "A company with this name already exists in the current tenant"
            )

        company = await self.repo.create(
            name=name,
            industry=industry,
            website=website,
            phone=phone,
            email=email,
            address=address,
            org_id=self._user.org_id,
        )

        await self.audit_service.log_create(
            entity_type="company",
            entity_id=company.id,
            after_values=self.audit_service.build_company_snapshot(company),
        )


        return company
    
    

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #

    async def get_company(
        self,
        company_id: str,
    ) -> Company:
        company = await self.repo.get_by_id(company_id)

        if company is None:
            raise EntityNotFoundError(
                f"Company {company_id} not found"
            )

        return company

    async def list_companies(
        self,
    ) -> List[Company]:
        return await self.repo.list()
    
    

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #

    async def update_company(
        self,
        company_id: str,
        *,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Company:
        company = await self.get_company(company_id)
        before_snapshot = self.audit_service.build_company_snapshot(company)

        update_data: dict[str, Any] = {}

        if name is not None:
            name = name.strip()

            if not name:
                raise BusinessRuleViolationError(
                    "Company name cannot be empty"
                )

            if name != company.name:
                duplicates = await self.repo.list(name=name)

                if any(
                    c.id != company.id
                    for c in duplicates
                ):
                    raise BusinessRuleViolationError(
                        "Another company with this name already exists in the current tenant"
                    )

            update_data["name"] = name

        if industry is not None:
            update_data["industry"] = industry

        if website is not None:
            update_data["website"] = website

        if phone is not None:
            update_data["phone"] = phone

        if email is not None:
            update_data["email"] = email

        if address is not None:
            update_data["address"] = address

        if not update_data:
            return company

        updated = await self.repo.update(
            company_id,
            **update_data,
        )

        if updated is None:
            raise EntityNotFoundError(
                f"Company {company_id} not found after update"
            )
        

        await self.audit_service.log_update(
            entity_type="company",
            entity_id=updated.id,
            before_values=before_snapshot,
            after_values=self.audit_service.build_company_snapshot(updated),
        )

        

        return updated

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #

    async def delete_company(
        self,
        company_id: str,
    ) -> bool:
        company = await self.get_company(company_id)

        before_snapshot = self.audit_service.build_company_snapshot(company)

        deleted = await self.repo.delete(company_id)

        if deleted:
            await self.audit_service.log_delete(
                entity_type="company",
                entity_id=company.id,
                before_values=before_snapshot,
            )

        return deleted