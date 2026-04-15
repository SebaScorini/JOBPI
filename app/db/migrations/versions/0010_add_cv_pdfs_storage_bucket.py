"""Add private cv-pdfs storage bucket.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-15
"""

from alembic import op
from sqlalchemy import inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = inspect(bind)
    schemas = set(inspector.get_schema_names())
    if "storage" not in schemas:
        return

    tables = {table_name for table_name in inspector.get_table_names(schema="storage")}
    if "buckets" not in tables:
        return

    op.execute(
        """
        insert into storage.buckets (id, name, public)
        values ('cv-pdfs', 'cv-pdfs', false)
        on conflict (id) do update
        set name = excluded.name,
            public = excluded.public
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = inspect(bind)
    schemas = set(inspector.get_schema_names())
    if "storage" not in schemas:
        return

    tables = {table_name for table_name in inspector.get_table_names(schema="storage")}
    if "buckets" not in tables:
        return

    op.execute(
        """
        delete from storage.buckets
        where id = 'cv-pdfs'
        """
    )
