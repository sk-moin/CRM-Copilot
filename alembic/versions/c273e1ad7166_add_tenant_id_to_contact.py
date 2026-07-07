"""add tenant_id to contact

Revision ID: c273e1ad7166
Revises: b72bfd60e489
Create Date: 2026-06-24 01:12:34.328139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c273e1ad7166'
down_revision: Union[str, Sequence[str], None] = 'b72bfd60e489'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
    "contact",
    sa.Column(
        "tenant_id",
        postgresql.UUID(as_uuid=True),
        nullable=True,
    ),
    )

    op.create_foreign_key(
        "fk_contact_tenant_id",
        "contact",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_contact_tenant_id",
        "contact",
        ["tenant_id"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index("ix_contact_tenant_id", table_name="contact")
    op.drop_constraint("fk_contact_tenant_id", "contact", type_="foreignkey")
    op.drop_column("contact", "tenant_id")