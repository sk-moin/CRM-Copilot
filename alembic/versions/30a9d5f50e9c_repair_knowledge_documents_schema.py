"""repair knowledge_documents schema

Revision ID: 1e92010d8baf
Revises: 27a9d5f50e9c
Create Date: 2026-07-07 19:00:51.779427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30a9d5f50e9c'
down_revision: Union[str, Sequence[str], None] = '27a9d5f50e9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        "knowledge_documents",
        sa.Column("storage_path", sa.String(), nullable=True),
    )

    op.add_column(
        "knowledge_documents",
        sa.Column("processing_started_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "knowledge_documents",
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "knowledge_documents",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.add_column(
        "knowledge_documents",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade():
    op.drop_column("knowledge_documents", "chunk_count")
    op.drop_column("knowledge_documents", "error_message")
    op.drop_column("knowledge_documents", "processed_at")
    op.drop_column("knowledge_documents", "processing_started_at")
    op.drop_column("knowledge_documents", "storage_path")
