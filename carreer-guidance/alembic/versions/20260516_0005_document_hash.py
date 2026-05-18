"""Add stable document identity fields.

Revision ID: 20260516_0005
Revises: 20260515_0004
Create Date: 2026-05-16 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260516_0005"
down_revision = "20260515_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("document") as batch:
        batch.add_column(sa.Column("source_key", sa.String(length=512), nullable=True))
        batch.add_column(
            sa.Column("content_hash", sa.String(length=128), nullable=True)
        )
        batch.create_index("ix_document_source_key", ["source_key"])
        batch.create_index("ix_document_content_hash", ["content_hash"])
        batch.create_unique_constraint(
            "uq_document_user_source_key",
            ["user_id", "source_key"],
        )

    op.execute(
        "UPDATE document SET source_key = document_name WHERE source_key IS NULL"
    )

    with op.batch_alter_table("document") as batch:
        batch.alter_column("source_key", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("document") as batch:
        batch.drop_constraint("uq_document_user_source_key", type_="unique")
        batch.drop_index("ix_document_content_hash")
        batch.drop_index("ix_document_source_key")
        batch.drop_column("content_hash")
        batch.drop_column("source_key")
