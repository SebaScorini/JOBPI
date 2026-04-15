"""Add updated_at and deleted_at columns to all tables.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table in ("users", "cvs", "job_analyses", "cv_job_matches"):
        existing_columns = {column["name"] for column in inspector.get_columns(table)}
        if "updated_at" not in existing_columns:
            op.add_column(
                table,
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            )
        if "deleted_at" not in existing_columns:
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    if bind.dialect.name == "postgresql":
        # Auto-update trigger for updated_at
        op.execute("""
            CREATE OR REPLACE FUNCTION public.update_updated_at_column()
            RETURNS trigger AS $$
            BEGIN
              NEW.updated_at = now();
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        for table in ("users", "cvs", "job_analyses", "cv_job_matches"):
            op.execute(f"DROP TRIGGER IF EXISTS set_updated_at ON public.{table}")
            op.execute(
                f"CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.{table} "
                f"FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column()"
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if bind.dialect.name == "postgresql":
        for table in ("users", "cvs", "job_analyses", "cv_job_matches"):
            op.execute(f"DROP TRIGGER IF EXISTS set_updated_at ON public.{table}")

    for table in ("users", "cvs", "job_analyses", "cv_job_matches"):
        existing_columns = {column["name"] for column in inspector.get_columns(table)}
        if "deleted_at" in existing_columns:
            op.drop_column(table, "deleted_at")
        if "updated_at" in existing_columns:
            op.drop_column(table, "updated_at")

    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS public.update_updated_at_column()")
