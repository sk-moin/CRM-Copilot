"""Change document chunk embedding dimension to 384.

Revision ID: 1d19d86d61d7
Revises: e273d1bc9120
"""

from typing import Sequence, Union

import pgvector
from alembic import op

# revision identifiers
revision: str = "1d19d86d61d7"
down_revision: Union[str, Sequence[str], None] = "e273d1bc9120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=1536),
        type_=pgvector.sqlalchemy.Vector(dim=384),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=384),
        type_=pgvector.sqlalchemy.Vector(dim=1536),
        existing_nullable=True,
    )