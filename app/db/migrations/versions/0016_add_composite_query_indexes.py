"""add composite indexes for common query patterns

Adds composite indexes that cover the most frequent query patterns:
- CV listing by user: (user_id, deleted_at, is_favorite DESC, created_at DESC)
- Job listing by user: (user_id, deleted_at, is_saved DESC, created_at DESC)
- Matches lookup by user+job: (user_id, job_id, deleted_at)
- Matches lookup by user+cv: (user_id, cv_id, deleted_at)
- Interview sessions by user+job: (user_id, job_id, deleted_at)
"""

from __future__ import annotations

from alembic import op


revision = "0016_add_composite_query_indexes"
down_revision = "0015_add_linkedin_generation_caches"
branch_labels = None
depends_on = None


def _postgres_index_sql() -> tuple[str, ...]:
    return (
        # CVs: user listing with soft-delete filter and sort
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cvs_user_active_sort "
        "ON cvs (user_id, deleted_at, is_favorite DESC, created_at DESC)",
        # Jobs: user listing with soft-delete filter and sort
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_analyses_user_active_sort "
        "ON job_analyses (user_id, deleted_at, is_saved DESC, created_at DESC)",
        # Matches: lookup by user+job (comparison, cascade delete)
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cv_job_matches_user_job_active "
        "ON cv_job_matches (user_id, job_id, deleted_at)",
        # Matches: lookup by user+cv (cascade delete on CV removal)
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cv_job_matches_user_cv_active "
        "ON cv_job_matches (user_id, cv_id, deleted_at)",
        # Interview sessions: listing by user+job
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_interview_sessions_user_job_active "
        "ON interview_sessions (user_id, job_id, deleted_at)",
    )


def _postgres_drop_index_sql() -> tuple[str, ...]:
    return (
        "DROP INDEX CONCURRENTLY IF EXISTS ix_interview_sessions_user_job_active",
        "DROP INDEX CONCURRENTLY IF EXISTS ix_cv_job_matches_user_cv_active",
        "DROP INDEX CONCURRENTLY IF EXISTS ix_cv_job_matches_user_job_active",
        "DROP INDEX CONCURRENTLY IF EXISTS ix_job_analyses_user_active_sort",
        "DROP INDEX CONCURRENTLY IF EXISTS ix_cvs_user_active_sort",
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    context = op.get_context()
    with context.autocommit_block():
        for statement in _postgres_index_sql():
            op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    context = op.get_context()
    with context.autocommit_block():
        for statement in _postgres_drop_index_sql():
            op.execute(statement)
