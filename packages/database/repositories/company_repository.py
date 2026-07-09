"""Company repository – thin wrapper around BaseRepository.

No custom behavior required; the class only sets the ``model`` attribute.
"""

from packages.database.models.company import Company
from packages.database.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository):
    """Repository for the ``Company`` model."""

    model = Company
