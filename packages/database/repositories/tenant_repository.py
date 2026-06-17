"""Tenant repository – thin wrapper around BaseRepository.

The repository does not need any custom methods; it simply provides the
``model`` attribute so that ``BaseRepository`` knows which ORM class to operate
on.
"""

from packages.database.models import Tenant
from packages.database.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository):
    """Repository for the ``Tenant`` model."""

    model = Tenant
