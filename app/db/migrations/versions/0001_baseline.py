"""baseline schema for users, cvs, job analyses, and matches"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def _json_type(dialect_name: str) -> sa.JSON:
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_array_default(dialect_name: str) -> sa.TextClause:
    if dialect_name == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    json_type = _json_type(dialect_name)
    json_array_default = _json_array_default(dialect_name)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "cvs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("clean_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("library_summary", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("tags", json_type, nullable=False, server_default=json_array_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_cvs_user_id", "cvs", ["user_id"], unique=False)
    op.create_index("ix_cvs_created_at", "cvs", ["created_at"], unique=False)

    op.create_table(
        "job_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("clean_description", sa.Text(), nullable=False),
        sa.Column("analysis_result", json_type, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'saved'")),
        sa.Column("applied_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("generated_cover_letter", sa.Text(), nullable=True),
        sa.Column("cover_letter_cv_id", sa.Integer(), nullable=True),
        sa.Column("cover_letter_language", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cover_letter_cv_id"], ["cvs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_job_analyses_user_id", "job_analyses", ["user_id"], unique=False)
    op.create_index("ix_job_analyses_cover_letter_cv_id", "job_analyses", ["cover_letter_cv_id"], unique=False)
    op.create_index("ix_job_analyses_created_at", "job_analyses", ["created_at"], unique=False)

    op.create_table(
        "cv_job_matches",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cv_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("fit_level", sa.String(length=50), nullable=False),
        sa.Column("fit_summary", sa.Text(), nullable=False),
        sa.Column("strengths", json_type, nullable=False),
        sa.Column("missing_skills", json_type, nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job_analyses.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "cv_id", "job_id", name="uq_cv_job_matches_user_cv_job"),
    )
    op.create_index("ix_cv_job_matches_user_id", "cv_job_matches", ["user_id"], unique=False)
    op.create_index("ix_cv_job_matches_cv_id", "cv_job_matches", ["cv_id"], unique=False)
    op.create_index("ix_cv_job_matches_job_id", "cv_job_matches", ["job_id"], unique=False)
    op.create_index("ix_cv_job_matches_created_at", "cv_job_matches", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cv_job_matches_created_at", table_name="cv_job_matches")
    op.drop_index("ix_cv_job_matches_job_id", table_name="cv_job_matches")
    op.drop_index("ix_cv_job_matches_cv_id", table_name="cv_job_matches")
    op.drop_index("ix_cv_job_matches_user_id", table_name="cv_job_matches")
    op.drop_table("cv_job_matches")

    op.drop_index("ix_job_analyses_created_at", table_name="job_analyses")
    op.drop_index("ix_job_analyses_cover_letter_cv_id", table_name="job_analyses")
    op.drop_index("ix_job_analyses_user_id", table_name="job_analyses")
    op.drop_table("job_analyses")

    op.drop_index("ix_cvs_created_at", table_name="cvs")
    op.drop_index("ix_cvs_user_id", table_name="cvs")
    op.drop_table("cvs")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
