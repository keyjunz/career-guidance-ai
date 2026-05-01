"""Initial database schema (squashed).

Revision ID: 20260326_0001
Revises:
Create Date: 2026-03-26 00:01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260326_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_role"),
    )
    op.create_index("ix_role_role", "role", ["role"], unique=True)

    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("password", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name="fk_user_role_id_role", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user"),
    )
    op.create_index("ix_user_user_name", "user", ["user_name"], unique=False)
    op.create_index("ix_user_is_active", "user", ["is_active"], unique=False)
    op.create_index("ix_user_email", "user", ["email"], unique=False)
    op.create_index("ix_user_role_id", "user", ["role_id"], unique=False)

    op.create_table(
        "conversation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_conversation_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversation"),
    )
    op.create_index(
        "ix_conversation_session_id", "conversation", ["session_id"], unique=False
    )
    op.create_index(
        "ix_conversation_user_id", "conversation", ["user_id"], unique=False
    )

    op.create_table(
        "request_cost_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_request_cost_log_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_request_cost_log"),
    )
    op.create_index(
        "ix_request_cost_log_user_id", "request_cost_log", ["user_id"], unique=False
    )
    op.create_index(
        "ix_request_cost_log_request_type",
        "request_cost_log",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        "ix_request_cost_log_model_name",
        "request_cost_log",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        "ix_request_cost_log_timestamp", "request_cost_log", ["timestamp"], unique=False
    )

    op.create_table(
        "document",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_name", sa.String(length=512), nullable=False),
        sa.Column("document_type", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ingestion_job_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_document_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document"),
    )
    op.create_index("ix_document_user_id", "document", ["user_id"], unique=False)
    op.create_index(
        "ix_document_document_name", "document", ["document_name"], unique=False
    )
    op.create_index(
        "ix_document_document_type", "document", ["document_type"], unique=False
    )
    op.create_index(
        "ix_document_ingestion_job_id", "document", ["ingestion_job_id"], unique=False
    )
    op.create_index("ix_document_status", "document", ["status"], unique=False)

    op.create_table(
        "message",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("chatbot_response", sa.Text(), nullable=False),
        sa.Column("cost_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation.id"],
            name="fk_message_conversation_id_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cost_log_id"],
            ["request_cost_log.id"],
            name="fk_message_cost_log_id_request_cost_log",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_message_user_id_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_message"),
    )
    op.create_index(
        "ix_message_conversation_id", "message", ["conversation_id"], unique=False
    )
    op.create_index("ix_message_cost_log_id", "message", ["cost_log_id"], unique=False)
    op.create_index("ix_message_user_id", "message", ["user_id"], unique=False)
    op.create_index("ix_message_timestamp", "message", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_timestamp", table_name="message")
    op.drop_index("ix_message_user_id", table_name="message")
    op.drop_index("ix_message_cost_log_id", table_name="message")
    op.drop_index("ix_message_conversation_id", table_name="message")
    op.drop_table("message")

    op.drop_index("ix_document_status", table_name="document")
    op.drop_index("ix_document_ingestion_job_id", table_name="document")
    op.drop_index("ix_document_document_type", table_name="document")
    op.drop_index("ix_document_document_name", table_name="document")
    op.drop_index("ix_document_user_id", table_name="document")
    op.drop_table("document")

    op.drop_index("ix_request_cost_log_timestamp", table_name="request_cost_log")
    op.drop_index("ix_request_cost_log_model_name", table_name="request_cost_log")
    op.drop_index("ix_request_cost_log_request_type", table_name="request_cost_log")
    op.drop_index("ix_request_cost_log_user_id", table_name="request_cost_log")
    op.drop_table("request_cost_log")

    op.drop_index("ix_conversation_user_id", table_name="conversation")
    op.drop_index("ix_conversation_session_id", table_name="conversation")
    op.drop_table("conversation")

    op.drop_index("ix_user_role_id", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_index("ix_user_is_active", table_name="user")
    op.drop_index("ix_user_user_name", table_name="user")
    op.drop_table("user")

    op.drop_index("ix_role_role", table_name="role")
    op.drop_table("role")
