"""add tenant_id to task

Revision ID: b72bfd60e489
Revises: 356d3e350370
Create Date: 2026-06-24 01:06:25.372717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b72bfd60e489'
down_revision: Union[str, Sequence[str], None] = '356d3e350370'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column(
        "task",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_task_tenant_id",
        "task",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_task_tenant_id",
        "task",
        ["tenant_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_task_tenant_id",
        table_name="task",
    )

    op.drop_constraint(
        "fk_task_tenant_id",
        "task",
        type_="foreignkey",
    )

    op.drop_column(
        "task",
        "tenant_id",
    )