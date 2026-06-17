"""User repository – thin wrapper around BaseRepository.

No custom methods are needed; the repository simply sets the ``model``
attribute so that ``BaseRepository`` knows which ORM class to operate on.
"""

from packages.database.models import User
from packages.database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for the ``User`` model."""

    model = User
