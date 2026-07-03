"""Add conversation and message tables

Revision ID: xxx_add_conversation_and_message
Revises: d273e1ab7816
Create Date: 2026-06-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5e19d9ef6749"
down_revision: Union[str, Sequence[str], None] = "d273e1ab7816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


conversation_status = sa.Enum(
    "active",
    "archived",
    name="conversation_status",
)

message_role = sa.Enum(
    "system",
    "user",
    "assistant",
    name="message_role",
)


def upgrade() -> None:
    """Upgrade schema."""

    conversation_status.create(op.get_bind(), checkfirst=True)
    message_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversation",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            conversation_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_conversation_tenant_user",
        "conversation",
        ["tenant_id", "user_id"],
    )

    op.create_index(
        "ix_conversation_tenant_status",
        "conversation",
        ["tenant_id", "status"],
    )

    op.create_index(
        "ix_conversation_created_at",
        "conversation",
        ["created_at"],
    )

    op.create_table(
        "message",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            message_role,
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "model",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "latency_ms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "finish_reason",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "message_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_message_conversation",
        "message",
        ["conversation_id", "created_at"],
    )

    op.create_index(
        "ix_message_tenant",
        "message",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_message_tenant", table_name="message")
    op.drop_index("ix_message_conversation", table_name="message")
    op.drop_table("message")

    op.drop_index("ix_conversation_created_at", table_name="conversation")
    op.drop_index("ix_conversation_tenant_status", table_name="conversation")
    op.drop_index("ix_conversation_tenant_user", table_name="conversation")
    op.drop_table("conversation")

    message_role.drop(op.get_bind(), checkfirst=True)
    conversation_status.drop(op.get_bind(), checkfirst=True)