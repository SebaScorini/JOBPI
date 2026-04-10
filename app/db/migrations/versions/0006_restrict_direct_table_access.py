"""restrict direct table access for non-backend roles"""

from __future__ import annotations

from alembic import op


revision = "0006_restrict_direct_table_access"
down_revision = "0005_add_integrity_and_dedupe_indexes"
branch_labels = None
depends_on = None


APP_TABLES = ("users", "cvs", "job_analyses", "cv_job_matches")


def _revoke_table_access_sql() -> tuple[str, ...]:
    statements: list[str] = []
    for table in APP_TABLES:
        statements.extend(
            [
                f"REVOKE ALL ON TABLE {table} FROM PUBLIC",
                f"REVOKE ALL ON TABLE {table} FROM anon",
                f"REVOKE ALL ON TABLE {table} FROM authenticated",
            ]
        )
    return tuple(statements)


def _revoke_sequence_access_sql() -> tuple[str, ...]:
    return (
        "REVOKE ALL ON SEQUENCE users_id_seq FROM PUBLIC",
        "REVOKE ALL ON SEQUENCE users_id_seq FROM anon",
        "REVOKE ALL ON SEQUENCE users_id_seq FROM authenticated",
        "REVOKE ALL ON SEQUENCE cvs_id_seq FROM PUBLIC",
        "REVOKE ALL ON SEQUENCE cvs_id_seq FROM anon",
        "REVOKE ALL ON SEQUENCE cvs_id_seq FROM authenticated",
        "REVOKE ALL ON SEQUENCE job_analyses_id_seq FROM PUBLIC",
        "REVOKE ALL ON SEQUENCE job_analyses_id_seq FROM anon",
        "REVOKE ALL ON SEQUENCE job_analyses_id_seq FROM authenticated",
        "REVOKE ALL ON SEQUENCE cv_job_matches_id_seq FROM PUBLIC",
        "REVOKE ALL ON SEQUENCE cv_job_matches_id_seq FROM anon",
        "REVOKE ALL ON SEQUENCE cv_job_matches_id_seq FROM authenticated",
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for statement in _revoke_table_access_sql():
        op.execute(statement)

    for statement in _revoke_sequence_access_sql():
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # We only restore the conservative default grants for direct table reads/writes.
    # Backend access should continue to be managed by the connection role itself.
    for table in APP_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO anon")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO authenticated")

    op.execute("GRANT USAGE, SELECT ON SEQUENCE users_id_seq TO anon")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE users_id_seq TO authenticated")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE cvs_id_seq TO anon")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE cvs_id_seq TO authenticated")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE job_analyses_id_seq TO anon")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE job_analyses_id_seq TO authenticated")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE cv_job_matches_id_seq TO anon")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE cv_job_matches_id_seq TO authenticated")
