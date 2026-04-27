"""enable row level security owner policies on public tables"""

from __future__ import annotations

from alembic import op


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


POLICY_STATEMENTS = (
    "ALTER TABLE users ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE users FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS users_select_own ON users",
    "DROP POLICY IF EXISTS users_insert_own ON users",
    "DROP POLICY IF EXISTS users_update_own ON users",
    "DROP POLICY IF EXISTS users_delete_own ON users",
    """
    CREATE POLICY users_select_own
    ON users
    FOR SELECT
    TO authenticated
    USING (supabase_user_id = auth.uid()::text AND deleted_at IS NULL)
    """,
    """
    CREATE POLICY users_insert_own
    ON users
    FOR INSERT
    TO authenticated
    WITH CHECK (supabase_user_id = auth.uid()::text)
    """,
    """
    CREATE POLICY users_update_own
    ON users
    FOR UPDATE
    TO authenticated
    USING (supabase_user_id = auth.uid()::text AND deleted_at IS NULL)
    WITH CHECK (supabase_user_id = auth.uid()::text)
    """,
    """
    CREATE POLICY users_delete_own
    ON users
    FOR DELETE
    TO authenticated
    USING (supabase_user_id = auth.uid()::text AND deleted_at IS NULL)
    """,
    "ALTER TABLE cvs ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE cvs FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS cvs_select_own ON cvs",
    "DROP POLICY IF EXISTS cvs_insert_own ON cvs",
    "DROP POLICY IF EXISTS cvs_update_own ON cvs",
    "DROP POLICY IF EXISTS cvs_delete_own ON cvs",
    """
    CREATE POLICY cvs_select_own
    ON cvs
    FOR SELECT
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cvs.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cvs_insert_own
    ON cvs
    FOR INSERT
    TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cvs.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cvs_update_own
    ON cvs
    FOR UPDATE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cvs.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cvs.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cvs_delete_own
    ON cvs
    FOR DELETE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cvs.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    "ALTER TABLE job_analyses ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE job_analyses FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS job_analyses_select_own ON job_analyses",
    "DROP POLICY IF EXISTS job_analyses_insert_own ON job_analyses",
    "DROP POLICY IF EXISTS job_analyses_update_own ON job_analyses",
    "DROP POLICY IF EXISTS job_analyses_delete_own ON job_analyses",
    """
    CREATE POLICY job_analyses_select_own
    ON job_analyses
    FOR SELECT
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = job_analyses.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY job_analyses_insert_own
    ON job_analyses
    FOR INSERT
    TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = job_analyses.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY job_analyses_update_own
    ON job_analyses
    FOR UPDATE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = job_analyses.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = job_analyses.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY job_analyses_delete_own
    ON job_analyses
    FOR DELETE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = job_analyses.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    "ALTER TABLE cv_job_matches ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE cv_job_matches FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS cv_job_matches_select_own ON cv_job_matches",
    "DROP POLICY IF EXISTS cv_job_matches_insert_own ON cv_job_matches",
    "DROP POLICY IF EXISTS cv_job_matches_update_own ON cv_job_matches",
    "DROP POLICY IF EXISTS cv_job_matches_delete_own ON cv_job_matches",
    """
    CREATE POLICY cv_job_matches_select_own
    ON cv_job_matches
    FOR SELECT
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cv_job_matches.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cv_job_matches_insert_own
    ON cv_job_matches
    FOR INSERT
    TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cv_job_matches.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cv_job_matches_update_own
    ON cv_job_matches
    FOR UPDATE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cv_job_matches.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cv_job_matches.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY cv_job_matches_delete_own
    ON cv_job_matches
    FOR DELETE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = cv_job_matches.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for statement in POLICY_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for statement in (
        "DROP POLICY IF EXISTS cv_job_matches_delete_own ON cv_job_matches",
        "DROP POLICY IF EXISTS cv_job_matches_update_own ON cv_job_matches",
        "DROP POLICY IF EXISTS cv_job_matches_insert_own ON cv_job_matches",
        "DROP POLICY IF EXISTS cv_job_matches_select_own ON cv_job_matches",
        "ALTER TABLE cv_job_matches NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE cv_job_matches DISABLE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS job_analyses_delete_own ON job_analyses",
        "DROP POLICY IF EXISTS job_analyses_update_own ON job_analyses",
        "DROP POLICY IF EXISTS job_analyses_insert_own ON job_analyses",
        "DROP POLICY IF EXISTS job_analyses_select_own ON job_analyses",
        "ALTER TABLE job_analyses NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE job_analyses DISABLE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS cvs_delete_own ON cvs",
        "DROP POLICY IF EXISTS cvs_update_own ON cvs",
        "DROP POLICY IF EXISTS cvs_insert_own ON cvs",
        "DROP POLICY IF EXISTS cvs_select_own ON cvs",
        "ALTER TABLE cvs NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE cvs DISABLE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS users_delete_own ON users",
        "DROP POLICY IF EXISTS users_update_own ON users",
        "DROP POLICY IF EXISTS users_insert_own ON users",
        "DROP POLICY IF EXISTS users_select_own ON users",
        "ALTER TABLE users NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE users DISABLE ROW LEVEL SECURITY",
    ):
        op.execute(statement)
