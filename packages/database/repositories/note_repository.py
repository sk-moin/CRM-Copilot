"""Note repository – thin wrapper around BaseRepository.

No custom methods required; the repository simply sets the ``model`` attribute.
"""

from packages.database.models.note import Note
from packages.database.repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository):
    """Repository for the ``Note`` model."""

    model = Note
