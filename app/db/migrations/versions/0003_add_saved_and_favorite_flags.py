"""add saved job and favorite cv flags"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable


revision = "0003_saved_favorite_flags"
down_revision = "0002_add_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {
        "job_analyses": set(),
        "cvs": set(),
    }

    try:
        inspector = inspect(bind)
        existing_columns = {
            table_name: {column["name"] for column in inspector.get_columns(table_name)}
            for table_name in ("job_analyses", "cvs")
        }
    except NoInspectionAvailable:
        pass

    if "is_saved" not in existing_columns.get("job_analyses", set()):
        op.add_column(
            "job_analyses",
            sa.Column("is_saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "is_favorite" not in existing_columns.get("cvs", set()):
        op.add_column(
            "cvs",
            sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("job_analyses", "is_saved", server_default=None)
        op.alter_column("cvs", "is_favorite", server_default=None)


def downgrade() -> None:
    op.drop_column("cvs", "is_favorite")
    op.drop_column("job_analyses", "is_saved")
