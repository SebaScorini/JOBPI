"""add integrity constraints and dedupe indexes"""

from __future__ import annotations

from alembic import op


revision = "0005_add_integrity_and_dedupe_indexes"
down_revision = "0004_add_list_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_job_analyses_status_valid'
            ) THEN
                ALTER TABLE job_analyses
                ADD CONSTRAINT ck_job_analyses_status_valid
                CHECK (status IN ('saved', 'applied', 'interview', 'rejected', 'offer'))
                NOT VALID;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE job_analyses VALIDATE CONSTRAINT ck_job_analyses_status_valid")

    context = op.get_context()
    with context.autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_users_email_lower "
            "ON users (lower(email))"
        )
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_cv_job_matches_one_recommended_per_job "
            "ON cv_job_matches (user_id, job_id) WHERE recommended"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cvs_user_clean_text_sha256 "
            "ON cvs (user_id, encode(digest(clean_text, 'sha256'), 'hex'))"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_user_title_company_clean_description_sha256 "
            "ON job_analyses (user_id, title, company, encode(digest(clean_description, 'sha256'), 'hex'))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    context = op.get_context()
    with context.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_user_title_company_clean_description_sha256")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_cvs_user_clean_text_sha256")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_cv_job_matches_one_recommended_per_job")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_users_email_lower")

    op.execute("ALTER TABLE job_analyses DROP CONSTRAINT IF EXISTS ck_job_analyses_status_valid")
