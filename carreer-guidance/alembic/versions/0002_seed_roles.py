"""Seed default roles and admin user.

Revision ID: 20260505_0002
Revises: 20260326_0001
Create Date: 2026-05-05 22:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260505_0002"
down_revision = "20260326_0001"
branch_labels = None
depends_on = None

ROLE_ADMIN_ID = "00000000-0000-0000-0000-000000000001"
ROLE_EMPLOYEE_ID = "00000000-0000-0000-0000-000000000002"
ROLE_CLIENT_ID = "00000000-0000-0000-0000-000000000003"
ADMIN_USER_ID = "00000000-0000-0000-0000-000000000010"

# bcrypt hash of "admin123"
ADMIN_PASSWORD_HASH = "$2b$12$LJ3m4ys3Lk0TSwHlbHv8UOQZbGChkVFMfcOqHYwJUWzNldSAjGjPu"


def upgrade() -> None:
    role_table = sa.table(
        "role",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role", sa.String),
    )
    op.bulk_insert(
        role_table,
        [
            {"id": ROLE_ADMIN_ID, "role": "admin"},
            {"id": ROLE_EMPLOYEE_ID, "role": "employee"},
            {"id": ROLE_CLIENT_ID, "role": "client"},
        ],
    )

    user_table = sa.table(
        "user",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("user_name", sa.String),
        sa.column("password", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("email", sa.Text),
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("phone", sa.String),
    )
    op.bulk_insert(
        user_table,
        [
            {
                "id": ADMIN_USER_ID,
                "user_name": "admin",
                "password": ADMIN_PASSWORD_HASH,
                "is_active": True,
                "email": "admin@system.local",
                "role_id": ROLE_ADMIN_ID,
                "phone": None,
            },
        ],
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM \"user\" WHERE id = '{ADMIN_USER_ID}'")
    op.execute(f"DELETE FROM role WHERE id IN ('{ROLE_ADMIN_ID}', '{ROLE_EMPLOYEE_ID}', '{ROLE_CLIENT_ID}')")
