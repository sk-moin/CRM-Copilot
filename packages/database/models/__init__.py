"""Re‑export database models for easy imports.

The project code and tests can now do:

    from packages.database.models import Base, Tenant, Organization, User

instead of importing each model individually.
"""

from .base import Base
from .tenant import Tenant
from .organization import Organization
from .user import User

# CRM Core
from .company import Company
from .contact import Contact
from .opportunity import Opportunity
from .task import Task
from .note import Note
