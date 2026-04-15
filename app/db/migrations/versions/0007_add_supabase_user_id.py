"""Add supabase_user_id column to users table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007"
down_revision = "0006_restrict_direct_table_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "supabase_user_id" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("supabase_user_id", sa.String(36), nullable=True),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_supabase_user_id" not in existing_indexes:
        op.create_index(
            "ix_users_supabase_user_id",
            "users",
            ["supabase_user_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("users")}
    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "ix_users_supabase_user_id" in existing_indexes:
        op.drop_index("ix_users_supabase_user_id", table_name="users")
    if "supabase_user_id" in existing_columns:
        op.drop_column("users", "supabase_user_id")
