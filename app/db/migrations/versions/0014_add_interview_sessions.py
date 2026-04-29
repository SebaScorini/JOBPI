"""add interview sessions"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_add_interview_sessions"
down_revision = "0013"
branch_labels = None
depends_on = None


POLICY_STATEMENTS = (
    "ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE interview_sessions FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS interview_sessions_select_own ON interview_sessions",
    "DROP POLICY IF EXISTS interview_sessions_insert_own ON interview_sessions",
    "DROP POLICY IF EXISTS interview_sessions_update_own ON interview_sessions",
    "DROP POLICY IF EXISTS interview_sessions_delete_own ON interview_sessions",
    """
    CREATE POLICY interview_sessions_select_own
    ON interview_sessions
    FOR SELECT
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = interview_sessions.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY interview_sessions_insert_own
    ON interview_sessions
    FOR INSERT
    TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = interview_sessions.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY interview_sessions_update_own
    ON interview_sessions
    FOR UPDATE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = interview_sessions.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    WITH CHECK (
      EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = interview_sessions.user_id
          AND users.supabase_user_id = auth.uid()::text
          AND users.deleted_at IS NULL
      )
    )
    """,
    """
    CREATE POLICY interview_sessions_delete_own
    ON interview_sessions
    FOR DELETE
    TO authenticated
    USING (
      deleted_at IS NULL
      AND EXISTS (
        SELECT 1
        FROM users
        WHERE users.id = interview_sessions.user_id
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

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_analyses.id"), nullable=False),
        sa.Column("cv_id", sa.Integer(), sa.ForeignKey("cvs.id"), nullable=False),
        sa.Column("session_type", sa.String(length=30), nullable=False, server_default=sa.text("'mixed'")),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evaluations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'in_progress'")),
        sa.Column("language", sa.String(length=20), nullable=False, server_default=sa.text("'english'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("session_type IN ('mixed', 'behavioral', 'technical')", name="ck_interview_sessions_session_type_valid"),
        sa.CheckConstraint("status IN ('in_progress', 'completed')", name="ck_interview_sessions_status_valid"),
    )

    for statement in POLICY_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for statement in (
        "DROP POLICY IF EXISTS interview_sessions_delete_own ON interview_sessions",
        "DROP POLICY IF EXISTS interview_sessions_update_own ON interview_sessions",
        "DROP POLICY IF EXISTS interview_sessions_insert_own ON interview_sessions",
        "DROP POLICY IF EXISTS interview_sessions_select_own ON interview_sessions",
        "ALTER TABLE interview_sessions NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE interview_sessions DISABLE ROW LEVEL SECURITY",
    ):
        op.execute(statement)

    op.drop_table("interview_sessions")