"""Organization repository – thin wrapper around BaseRepository.

No custom behavior required; the class only sets the ``model`` attribute.
"""

from packages.database.models import Organization
from packages.database.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository):
    """Repository for the ``Organization`` model."""

    model = Organization
