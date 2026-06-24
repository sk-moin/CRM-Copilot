"""Task repository – thin wrapper around BaseRepository.

No custom methods required; the repository simply sets the ``model`` attribute.
"""

from packages.database.models.task import Task
from packages.database.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository):
    """Repository for the ``Task`` model."""

    model = Task