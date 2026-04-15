"""Backfill supabase_user_id for legacy users by email.

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-15
"""

from alembic import op
from sqlalchemy import inspect

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = inspect(bind)
    schemas = set(inspector.get_schema_names())
    if "auth" not in schemas:
        return

    auth_tables = {table_name for table_name in inspector.get_table_names(schema="auth")}
    public_tables = {table_name for table_name in inspector.get_table_names(schema="public")}
    if "users" not in auth_tables or "users" not in public_tables:
        return

    op.execute(
        """
        update public.users as u
        set supabase_user_id = au.id::text
        from auth.users as au
        where u.supabase_user_id is null
          and au.email is not null
          and au.email <> ''
          and lower(au.email) = lower(u.email)
          and not exists (
              select 1
              from public.users as linked
              where linked.supabase_user_id = au.id::text
          )
        """
    )


def downgrade() -> None:
    pass
