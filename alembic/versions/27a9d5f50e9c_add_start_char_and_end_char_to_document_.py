"""add start_char and end_char to document_chunks"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "27a9d5f50e9c"
down_revision = "1d19d86d61d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "start_char",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "document_chunks",
        sa.Column(
            "end_char",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "start_char")
    op.drop_column("document_chunks", "end_char")