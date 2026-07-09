"""Opportunity repository – thin wrapper around BaseRepository.

No custom methods required; the repository simply sets the ``model`` attribute.
"""

from packages.database.models.opportunity import Opportunity
from packages.database.repositories.base_repository import BaseRepository


class OpportunityRepository(BaseRepository):
    """Repository for the ``Opportunity`` model."""

    model = Opportunity
