"""Add retrieval trace and retrieved chunk tables

Revision ID: 86ce2429d0a0
Revises: 30a9d5f50e9c
Create Date: 2026-07-08 15:52:16.482700
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "86ce2429d0a0"
down_revision: Union[str, Sequence[str], None] = "30a9d5f50e9c"
branch_labels = None
depends_on = None


retrieval_trace_status = postgresql.ENUM(
    "success",
    "failed",
    name="retrieval_trace_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    retrieval_trace_status.create(bind, checkfirst=True)

    op.create_table(
        "retrieval_traces",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        sa.Column(
            "query",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "embedding_model",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "vector_store",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "embedding_latency_ms",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "retrieval_latency_ms",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "total_latency_ms",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "retrieved_chunks",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),

        sa.Column(
            "status",
            retrieval_trace_status,
            nullable=False,
            server_default=sa.text("'success'"),
        ),

        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "retrieval_metadata",
            sa.JSON(),
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
            ["conversation_id"],
            ["conversation.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_retrieval_traces_created_at",
        "retrieval_traces",
        ["created_at"],
    )

    op.create_index(
        "ix_retrieval_traces_conversation_id",
        "retrieval_traces",
        ["conversation_id"],
    )

    op.create_index(
        "ix_retrieval_traces_status",
        "retrieval_traces",
        ["status"],
    )

    op.create_table(
        "retrieved_chunks",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "rank",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "similarity_score",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "chunk_preview",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "retrieval_metadata",
            sa.JSON(),
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
            ["trace_id"],
            ["retrieval_traces.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="CASCADE",
        ),

        sa.CheckConstraint(
            "rank > 0",
            name="ck_rank_positive",
        ),

        sa.CheckConstraint(
            "similarity_score >= 0 AND similarity_score <= 1",
            name="ck_similarity_score",
        ),
    )

    op.create_index(
        "ix_retrieved_chunks_trace_id",
        "retrieved_chunks",
        ["trace_id"],
    )

    op.create_index(
        "ix_retrieved_chunks_document_id",
        "retrieved_chunks",
        ["document_id"],
    )

    op.create_index(
        "ix_retrieved_chunks_similarity_score",
        "retrieved_chunks",
        ["similarity_score"],
    )

    op.create_index(
        "ix_retrieved_chunks_trace_rank",
        "retrieved_chunks",
        ["trace_id", "rank"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieved_chunks_trace_rank",
        table_name="retrieved_chunks",
    )

    op.drop_index(
        "ix_retrieved_chunks_similarity_score",
        table_name="retrieved_chunks",
    )

    op.drop_index(
        "ix_retrieved_chunks_document_id",
        table_name="retrieved_chunks",
    )

    op.drop_index(
        "ix_retrieved_chunks_trace_id",
        table_name="retrieved_chunks",
    )

    op.drop_table("retrieved_chunks")

    op.drop_index(
        "ix_retrieval_traces_status",
        table_name="retrieval_traces",
    )

    op.drop_index(
        "ix_retrieval_traces_conversation_id",
        table_name="retrieval_traces",
    )

    op.drop_index(
        "ix_retrieval_traces_created_at",
        table_name="retrieval_traces",
    )

    op.drop_table("retrieval_traces")

    bind = op.get_bind()
    retrieval_trace_status.drop(bind, checkfirst=True)