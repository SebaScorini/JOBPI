"""add linkedin generation caches"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0015_add_linkedin_generation_caches"
down_revision = "0014_add_interview_sessions"
branch_labels = None
depends_on = None


def _json_type(dialect_name: str) -> sa.JSON:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_object_default(dialect_name: str) -> sa.TextClause:
    if dialect_name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    json_type = _json_type(bind.dialect.name)
    json_default = _json_object_default(bind.dialect.name)

    cv_columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "linkedin_profile_cache" not in cv_columns:
        op.add_column(
            "cvs",
            sa.Column("linkedin_profile_cache", json_type, nullable=False, server_default=json_default),
        )

    job_columns = {column["name"] for column in inspector.get_columns("job_analyses")}
    if "linkedin_outreach_cache" not in job_columns:
        op.add_column(
            "job_analyses",
            sa.Column("linkedin_outreach_cache", json_type, nullable=False, server_default=json_default),
        )
    if bind.dialect.name != "sqlite":
        for table_name, column_name in (
            ("cvs", "linkedin_profile_cache"),
            ("job_analyses", "linkedin_outreach_cache"),
        ):
            op.alter_column(table_name, column_name, server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    job_columns = {column["name"] for column in inspector.get_columns("job_analyses")}
    if "linkedin_outreach_cache" in job_columns:
        op.drop_column("job_analyses", "linkedin_outreach_cache")

    cv_columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "linkedin_profile_cache" in cv_columns:
        op.drop_column("cvs", "linkedin_profile_cache")
