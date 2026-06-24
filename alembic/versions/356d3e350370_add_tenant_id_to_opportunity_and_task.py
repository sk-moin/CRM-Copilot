"""add tenant_id to opportunity

Revision ID: 356d3e350370
Revises: c97b2553d48f
Create Date: 2026-06-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = "356d3e350370"
down_revision: Union[str, Sequence[str], None] = "c97b2553d48f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunity",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_opportunity_tenant_id",
        "opportunity",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_opportunity_tenant_id",
        "opportunity",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_tenant_id",
        table_name="opportunity",
    )

    op.drop_constraint(
        "fk_opportunity_tenant_id",
        "opportunity",
        type_="foreignkey",
    )

    op.drop_column(
        "opportunity",
        "tenant_id",
    )