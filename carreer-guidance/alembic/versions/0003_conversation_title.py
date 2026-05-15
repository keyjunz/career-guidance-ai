"""Add optional title to conversation.

Revision ID: 20260513_0003
Revises: 20260505_0002
Create Date: 2026-05-13 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260513_0003"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation",
        sa.Column("title", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation", "title")
