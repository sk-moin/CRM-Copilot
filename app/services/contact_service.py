from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models.contact import Contact
from packages.database.repositories.contact_repository import ContactRepository
from packages.database.repositories.company_repository import CompanyRepository

from app.services.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
)


class ContactService:
    """
    Service layer for Contact CRUD operations.

    All repository queries are automatically tenant-scoped through the
    tenant_id passed to the repository constructor.
    """

    def __init__(self, session: AsyncSession, current_user: Any):
        tenant_id = current_user.organization.tenant_id

        self.repo = ContactRepository(session=session, tenant_id=tenant_id)
        self.company_repo = CompanyRepository(
            session=session,
            tenant_id=tenant_id,
        )

        self._user = current_user

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #
    async def create_contact(
        self,
        *,
        first_name: str,
        last_name: str,
        company_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        job_title: Optional[str] = None,
    ) -> Contact:
        """Create a new contact."""

        if not first_name:
            raise BusinessRuleViolationError("first_name is required")

        if not last_name:
            raise BusinessRuleViolationError("last_name is required")

        if not company_id:
            raise BusinessRuleViolationError("company_id is required")
        
        company = await self.company_repo.get_by_id(company_id)
        
        if company is None:
                raise EntityNotFoundError(
                    f"Company {company_id} not found"
                )

        return await self.repo.create(
            first_name=first_name,
            last_name=last_name,
            company_id=company_id,
            email=email,
            phone=phone,
            job_title=job_title,
            org_id=self._user.org_id,
            tenant_id=self._user.tenant_id,
        )

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #
    async def get_contact(self, contact_id: str) -> Contact:
        """Get a contact by ID."""

        contact = await self.repo.get_by_id(contact_id)

        if contact is None:
            raise EntityNotFoundError(
                f"Contact {contact_id} not found"
            )

        return contact

    async def list_contacts(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Contact]:
        """List contacts with optional filters."""

        return await self.repo.list(**(filters or {}))

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    async def update_contact(
        self,
        contact_id: str,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        job_title: Optional[str] = None,
    ) -> Contact:
        """Update a contact."""

        contact = await self.get_contact(contact_id)

        if company_id is not None:
            company = await self.company_repo.get_by_id(company_id)
            if company is None:
                raise EntityNotFoundError(
                    f"Company {company_id} not found"
                )

        update_data: Dict[str, Any] = {}

        if first_name is not None:
            update_data["first_name"] = first_name

        if last_name is not None:
            update_data["last_name"] = last_name

        if company_id is not None:
            update_data["company_id"] = company_id

        if email is not None:
            update_data["email"] = email

        if phone is not None:
            update_data["phone"] = phone

        if job_title is not None:
            update_data["job_title"] = job_title

        if not update_data:
            return contact

        updated = await self.repo.update(contact_id, **update_data)

        if updated is None:
            raise EntityNotFoundError(
                f"Contact {contact_id} not found after update"
            )

        return updated

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #
    async def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact."""

        contact = await self.get_contact(contact_id)

        deleted = await self.repo.delete(contact.id)

        if not deleted:
            raise EntityNotFoundError(
                f"Contact {contact_id} not found"
            )

        return True