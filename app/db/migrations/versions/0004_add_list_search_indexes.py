"""add list and search indexes for cvs and jobs"""

from __future__ import annotations

from alembic import op


revision = "0004_add_list_search_indexes"
down_revision = "0003_saved_favorite_flags"
branch_labels = None
depends_on = None


def _postgres_index_sql() -> tuple[str, ...]:
    return (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cvs_user_favorite_created_at "
        "ON cvs (user_id, is_favorite DESC, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_user_saved_created_at "
        "ON job_analyses (user_id, is_saved, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cvs_display_name_trgm "
        "ON cvs USING GIN (lower(display_name) gin_trgm_ops)",
    )


def _postgres_drop_index_sql() -> tuple[str, ...]:
    return (
        "DROP INDEX CONCURRENTLY IF EXISTS idx_cvs_display_name_trgm",
        "DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_user_saved_created_at",
        "DROP INDEX CONCURRENTLY IF EXISTS idx_cvs_user_favorite_created_at",
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

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
