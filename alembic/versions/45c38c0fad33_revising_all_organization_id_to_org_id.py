"""revising all organization_id to org_id

Revision ID: 45c38c0fad33
Revises: 87ce2430d1a1
Create Date: 2026-07-31 17:20:26.831139

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '45c38c0fad33'
down_revision: Union[str, Sequence[str], None] = '87ce2430d1a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "knowledge_documents",
        "organization_id",
        new_column_name="org_id",
    )

def downgrade():
    op.alter_column(
        "knowledge_documents",
        "org_id",
        new_column_name="organization_id",
    )
