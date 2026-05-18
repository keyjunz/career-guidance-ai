"""Add image urls to messages.

Revision ID: 20260516_0006
Revises: 20260516_0005
Create Date: 2026-05-16 00:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260516_0006"
down_revision = "20260516_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("message") as batch:
        batch.add_column(sa.Column("image_urls", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("message") as batch:
        batch.drop_column("image_urls")
