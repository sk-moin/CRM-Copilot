"""add tenant_id to user

Revision ID: 42c06b8d0a9f
Revises: a544e3a513a2
Create Date: 2026-06-22 19:04:05.199600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '42c06b8d0a9f'
down_revision: Union[str, Sequence[str], None] = 'a544e3a513a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_user_tenant",
        "user",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_user_tenant_id",
        "user",
        ["tenant_id"],
    )

    # Existing rows backfill if necessary

    op.alter_column(
        "user",
        "tenant_id",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
