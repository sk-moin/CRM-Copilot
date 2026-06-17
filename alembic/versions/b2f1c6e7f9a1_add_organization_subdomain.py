"""Add unique subdomain column to organization table

Revision ID: b2f1c6e7f9a1
Revises: a8617753f0e8
Create Date: 2026-06-17 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2f1c6e7f9a1"
down_revision = "a8617753f0e8"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Step A – add nullable column
    op.add_column(
        "organization",
        sa.Column(
            "subdomain",
            sa.String(),
            nullable=True,
            comment="Unique organization subdomain",
        ),
    )
    # Step B – backfill deterministic values
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE organization
            SET subdomain = CONCAT('org-', CAST(id AS TEXT));
            """
        )
    )
    # Step C – make NOT NULL
    op.alter_column("organization", "subdomain", nullable=False)
    # Step D – create unique index
    op.create_index(
        op.f("ix_organization_subdomain"),
        "organization",
        ["subdomain"],
        unique=True,
    )

def downgrade() -> None:
    op.drop_index(op.f("ix_organization_subdomain"), table_name="organization")
    op.alter_column("organization", "subdomain", nullable=True)
    op.drop_column("organization", "subdomain")
