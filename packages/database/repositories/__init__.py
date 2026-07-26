"""Repository exports for the CRM Copilot multi‑tenant system.

All repositories inherit from ``BaseRepository`` and are tenant‑scoped via the
organization (``org_id``) to enforce strict data isolation.
"""

from packages.database.repositories.company_repository import (
    CompanyRepository,
)
from packages.database.repositories.contact_repository import (
    ContactRepository,
)
from packages.database.repositories.opportunity_repository import (
    OpportunityRepository,
)
from packages.database.repositories.task_repository import (
    TaskRepository,
)
from packages.database.repositories.note_repository import (
    NoteRepository,
)
from packages.database.repositories.base_repository import (
    BaseRepository,
)
from packages.database.repositories.prompt_repository import (
    PromptRepository,
)
from packages.database.repositories.prompt_version_repository import (
    PromptVersionRepository,
)

__all__ = [
    "CompanyRepository",
    "ContactRepository",
    "OpportunityRepository",
    "TaskRepository",
    "NoteRepository",
    "BaseRepository",
    "PromptRepository",
    "PromptVersionRepository",
]
