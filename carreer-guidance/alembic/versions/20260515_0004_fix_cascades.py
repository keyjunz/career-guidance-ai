"""Fix conversation and message cascades to prevent NOT NULL violations.

Revision ID: 20260515_0004
Revises: 20260513_0003
Create Date: 2026-05-15 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260515_0004"
down_revision = "20260513_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure ON DELETE CASCADE is properly set on message -> conversation
    # We drop and recreate to be absolutely sure it's correct in the DB
    op.drop_constraint(
        "fk_message_conversation_id_conversation", "message", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_message_conversation_id_conversation",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Ensure ON DELETE CASCADE is properly set on conversation -> user
    op.drop_constraint(
        "fk_conversation_user_id_user", "conversation", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_conversation_user_id_user",
        "conversation",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Ensure ON DELETE CASCADE is properly set on message -> user
    op.drop_constraint("fk_message_user_id_user", "message", type_="foreignkey")
    op.create_foreign_key(
        "fk_message_user_id_user",
        "message",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Ensure ON DELETE CASCADE is properly set on document -> user
    op.drop_constraint("fk_document_user_id_user", "document", type_="foreignkey")
    op.create_foreign_key(
        "fk_document_user_id_user",
        "document",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Ensure ON DELETE CASCADE is properly set on request_cost_log -> user
    op.drop_constraint(
        "fk_request_cost_log_user_id_user", "request_cost_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_request_cost_log_user_id_user",
        "request_cost_log",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert to standard foreign keys (without explicit CASCADE if that was the state, 
    # though 0001 had them, we keep them for safety in downgrade)
    op.drop_constraint(
        "fk_request_cost_log_user_id_user", "request_cost_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_request_cost_log_user_id_user",
        "request_cost_log",
        "user",
        ["user_id"],
        ["id"],
    )

    op.drop_constraint("fk_document_user_id_user", "document", type_="foreignkey")
    op.create_foreign_key(
        "fk_document_user_id_user", "document", "user", ["user_id"], ["id"]
    )

    op.drop_constraint("fk_message_user_id_user", "message", type_="foreignkey")
    op.create_foreign_key(
        "fk_message_user_id_user", "message", "user", ["user_id"], ["id"]
    )

    op.drop_constraint(
        "fk_conversation_user_id_user", "conversation", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_conversation_user_id_user", "conversation", "user", ["user_id"], ["id"]
    )

    op.drop_constraint(
        "fk_message_conversation_id_conversation", "message", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_message_conversation_id_conversation",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
