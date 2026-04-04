"""add performance indexes for user-scoped lists and tag search"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable


revision = "0002_add_performance_indexes"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_indexes = {
        "cvs": set(),
        "job_analyses": set(),
        "cv_job_matches": set(),
    }

    try:
        inspector = inspect(bind)
        existing_indexes = {
            table_name: {index["name"] for index in inspector.get_indexes(table_name)}
            for table_name in ("cvs", "job_analyses", "cv_job_matches")
        }
    except NoInspectionAvailable:
        pass

    standard_indexes = [
        ("idx_cvs_user_id_created_at", "cvs", ["user_id", "created_at"]),
        ("idx_jobs_user_id_created_at", "job_analyses", ["user_id", "created_at"]),
        ("idx_matches_user_id_created_at", "cv_job_matches", ["user_id", "created_at"]),
    ]

    for index_name, table_name, columns in standard_indexes:
        if index_name not in existing_indexes.get(table_name, set()):
            op.create_index(index_name, table_name, columns, unique=False, if_not_exists=True)

    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS idx_cvs_tags_gin ON cvs USING GIN (tags)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_cvs_tags_gin")

    op.drop_index("idx_matches_user_id_created_at", table_name="cv_job_matches")
    op.drop_index("idx_jobs_user_id_created_at", table_name="job_analyses")
    op.drop_index("idx_cvs_user_id_created_at", table_name="cvs")
