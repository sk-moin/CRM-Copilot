"""Contact repository – thin wrapper around BaseRepository.

No custom methods required; the repository simply sets the ``model``
attribute so that ``BaseRepository`` knows which ORM class to operate on.
"""

from packages.database.models.contact import Contact
from packages.database.repositories.base_repository import BaseRepository


class ContactRepository(BaseRepository):
    """Repository for the ``Contact`` model."""

    model = Contact