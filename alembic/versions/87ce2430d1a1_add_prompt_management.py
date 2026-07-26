"""Add prompt management tables

Revision ID: 87ce2430d1a1
Revises: 86ce2429d0a0
Create Date: 2026-07-21 18:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "87ce2430d1a1"
down_revision: Union[str, Sequence[str], None] = "86ce2429d0a0"
branch_labels = None
depends_on = None


prompt_category = postgresql.ENUM(
    "system",
    "agent",
    "rag",
    "tool",
    "summarization",
    "classification",
    "action",
    "custom",
    name="prompt_category",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    prompt_category.create(bind, checkfirst=True)

    op.create_table(
        "prompt",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),

        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "category",
            prompt_category,
            nullable=False,
            server_default=sa.text("'system'"),
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organization.id"],
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint(
            "org_id",
            "name",
            name="uq_prompt_org_name",
        ),
    )

    op.create_index(
        "ix_prompt_tenant_id",
        "prompt",
        ["tenant_id"],
    )

    op.create_index(
        "ix_prompt_org_id",
        "prompt",
        ["org_id"],
    )

    op.create_index(
        "ix_prompt_category",
        "prompt",
        ["category"],
    )

    op.create_table(
        "prompt_version",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),

        sa.Column(
            "prompt_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "template",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "variables",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),

        sa.Column(
            "llm_model",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.2"),
        ),

        sa.Column(
            "top_p",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),

        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "response_format",
            postgresql.JSONB(),
            nullable=True,
        ),

        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),

        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),


        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["prompt.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="SET NULL",
        ),

        sa.UniqueConstraint(
            "prompt_id",
            "version",
            name="uq_prompt_version",
        ),
    )

    op.create_index(
        "ix_prompt_version_prompt_id",
        "prompt_version",
        ["prompt_id"],
    )

    op.create_index(
        "ix_prompt_version_created_by",
        "prompt_version",
        ["created_by"],
    )

    op.create_index(
        "ix_prompt_version_version",
        "prompt_version",
        ["version"],
    )

    op.add_column(
        "prompt",
        sa.Column(
            "active_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_prompt_active_version",
        "prompt",
        "prompt_version",
        ["active_version_id"],
        ["id"],
        ondelete="SET NULL",
    )



def downgrade() -> None:
    op.drop_index(
        "ix_prompt_version_version",
        table_name="prompt_version",
    )

    op.drop_index(
        "ix_prompt_version_created_by",
        table_name="prompt_version",
    )

    op.drop_index(
        "ix_prompt_version_prompt_id",
        table_name="prompt_version",
    )

    op.drop_table("prompt_version")

    op.drop_index(
        "ix_prompt_category",
        table_name="prompt",
    )

    op.drop_index(
        "ix_prompt_org_id",
        table_name="prompt",
    )

    op.drop_index(
        "ix_prompt_tenant_id",
        table_name="prompt",
    )

    op.drop_constraint(
        "fk_prompt_active_version",
        "prompt",
        type_="foreignkey",
    )

    op.drop_column(
        "prompt",
        "active_version_id",
    )

    op.drop_table("prompt")

    bind = op.get_bind()
    prompt_category.drop(bind, checkfirst=True)